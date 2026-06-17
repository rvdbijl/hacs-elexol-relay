"""UDP hub for Elexol EtherIO relay boards."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import timedelta
import logging
import socket
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval

from .const import PORTS

_LOGGER = logging.getLogger(__name__)

RelayStateCallback = Callable[[], None]
READ_TIMEOUT = 1.0


class ElexolRelayHub:
    """Own the Elexol UDP socket protocol and board readback state."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        udp_port: int,
        ports: list[str],
        poll_interval: int,
    ) -> None:
        """Initialize the relay hub."""
        self.hass = hass
        self.host = host
        self.udp_port = udp_port
        self.ports = tuple(port.upper() for port in ports)
        self.poll_interval = poll_interval
        self.port_states: dict[str, int] = {port: 0 for port in PORTS}
        self.available = False
        self.last_error: str | None = None
        self._verification_failed_ports: set[str] = set()
        self._lock = asyncio.Lock()
        self._listeners: set[RelayStateCallback] = set()
        self._unsub_poll: Callable[[], None] | None = None

    async def async_initialize(self) -> None:
        """Read configured ports from the board before entities are created."""
        await self.async_refresh_all_ports()
        if self.poll_interval > 0:
            self._unsub_poll = async_track_time_interval(
                self.hass,
                self._schedule_refresh,
                timedelta(seconds=self.poll_interval),
            )

    @callback
    def async_stop(self) -> None:
        """Stop background polling."""
        if self._unsub_poll is not None:
            self._unsub_poll()
            self._unsub_poll = None

    @callback
    def async_add_listener(self, listener: RelayStateCallback) -> Callable[[], None]:
        """Register a listener for readback state changes."""
        self._listeners.add(listener)

        @callback
        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    @callback
    def _async_notify_listeners(self) -> None:
        """Notify entities that cached state changed."""
        for listener in list(self._listeners):
            listener()

    @callback
    def _schedule_refresh(self, *args: Any) -> None:
        """Schedule a polling refresh."""
        self.hass.async_create_task(self.async_refresh_all_ports())

    def relay_is_on(self, port: str, relay: int) -> bool:
        """Return whether the last readback says a relay bit is on."""
        port = port.upper()
        bit = 1 << (relay - 1)
        return bool(self.port_states[port] & bit)

    def port_value(self, port: str) -> int:
        """Return the last readback value for a port."""
        return self.port_states[port.upper()]

    def port_verified(self, port: str) -> bool:
        """Return whether the port has no known write verification failure."""
        return port.upper() not in self._verification_failed_ports

    async def async_refresh_all_ports(self) -> None:
        """Read every configured port from the board."""
        changed = False
        async with self._lock:
            previous_available = self.available
            previous_error = self.last_error
            try:
                for port in self.ports:
                    value = await self._async_read_port_locked(port)
                    if self.port_states[port] != value:
                        self.port_states[port] = value
                        changed = True
                self.available = True
                self.last_error = None
            except HomeAssistantError as err:
                self.available = False
                self.last_error = str(err)
                changed = True
                _LOGGER.warning("Unable to refresh Elexol relay state: %s", err)

            if self.available != previous_available or self.last_error != previous_error:
                changed = True

        if changed:
            self._async_notify_listeners()

    async def async_set_relay(self, port: str, relay: int, state: bool) -> None:
        """Set one relay, then verify by reading the physical port value."""
        port = port.upper()
        bit = 1 << (relay - 1)
        should_notify = False

        try:
            async with self._lock:
                current = self.port_states[port]
                next_value = current | bit if state else current & ~bit
                if next_value == current and self.available:
                    return

                should_notify = True
                await self._async_write_and_verify_port_locked(port, next_value)
        finally:
            if should_notify:
                self._async_notify_listeners()

    async def async_send_port(self, port: str, value: int) -> None:
        """Send a complete port mask, then verify by reading it back."""
        port = port.upper()
        value = int(value)
        if value < 0 or value > 255:
            raise HomeAssistantError(f"Elexol port value must be 0-255, got {value}")

        try:
            async with self._lock:
                await self._async_write_and_verify_port_locked(port, value)
        finally:
            self._async_notify_listeners()

    async def _async_write_and_verify_port_locked(self, port: str, value: int) -> None:
        """Write a port mask and update state from the readback response."""
        try:
            await self._async_send_port_locked(port, value)
            readback = await self._async_read_port_locked(port)
        except HomeAssistantError as err:
            self.available = False
            self.last_error = str(err)
            raise

        self.port_states[port] = readback
        self.available = True

        if readback == value:
            self._verification_failed_ports.discard(port)
            self.last_error = None
            return

        self._verification_failed_ports.add(port)
        self.last_error = (
            f"Port {port} readback 0x{readback:02x} did not match "
            f"commanded value 0x{value:02x}"
        )
        raise HomeAssistantError(self.last_error)

    async def _async_send_port_locked(self, port: str, value: int) -> None:
        """Send one uppercase port write packet. Caller must hold the lock."""
        packet = bytes((ord(port.upper()), value))
        _LOGGER.debug(
            "Sending Elexol relay packet to %s:%s: %r",
            self.host,
            self.udp_port,
            packet,
        )
        await self.hass.async_add_executor_job(
            _send_udp_packet,
            self.host,
            self.udp_port,
            packet,
        )

    async def _async_read_port_locked(self, port: str) -> int:
        """Send one lowercase port read command and return the port value."""
        command = port.lower()
        packet = command.encode("ascii")
        response = await self.hass.async_add_executor_job(
            _read_udp_packet,
            self.host,
            self.udp_port,
            packet,
            READ_TIMEOUT,
        )
        value = _parse_port_read_response(command, response)
        _LOGGER.debug(
            "Read Elexol port %s from %s:%s as 0x%02x via %r",
            port,
            self.host,
            self.udp_port,
            value,
            response,
        )
        return value


def _send_udp_packet(host: str, udp_port: int, packet: bytes) -> None:
    """Send a UDP packet to the relay board."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(packet, (host, udp_port))
    except OSError as err:
        raise HomeAssistantError(
            f"Failed to send Elexol UDP packet to {host}:{udp_port}: {err}"
        ) from err


def _read_udp_packet(host: str, udp_port: int, packet: bytes, timeout: float) -> bytes:
    """Send a UDP read command and wait for the board response."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(packet, (host, udp_port))
            response, _addr = sock.recvfrom(64)
            return response
    except socket.timeout as err:
        raise HomeAssistantError(
            f"Timed out waiting for Elexol UDP readback from {host}:{udp_port}"
        ) from err
    except OSError as err:
        raise HomeAssistantError(
            f"Failed to read Elexol UDP packet from {host}:{udp_port}: {err}"
        ) from err


def _parse_port_read_response(command: str, response: bytes) -> int:
    """Parse an Ether I/O 24 R port-read response."""
    expected_codes = {ord(command.lower()), ord(command.upper())}
    if len(response) >= 2 and response[0] in expected_codes:
        return response[1]
    if len(response) == 1:
        return response[0]
    raise HomeAssistantError(
        f"Unexpected Elexol readback response for {command!r}: {response!r}"
    )
