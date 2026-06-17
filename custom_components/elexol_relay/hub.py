"""UDP hub for Elexol EtherIO relay boards."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
import socket

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import PORTS

_LOGGER = logging.getLogger(__name__)

RelayStateCallback = Callable[[], None]


class ElexolRelayHub:
    """Own the Elexol UDP socket protocol and optimistic relay state."""

    def __init__(self, hass: HomeAssistant, host: str, udp_port: int, ports: list[str]) -> None:
        """Initialize the relay hub."""
        self.hass = hass
        self.host = host
        self.udp_port = udp_port
        self.ports = tuple(port.upper() for port in ports)
        self.port_states: dict[str, int] = {port: 0 for port in PORTS}
        self._lock = asyncio.Lock()
        self._listeners: set[RelayStateCallback] = set()

    @callback
    def async_add_listener(self, listener: RelayStateCallback) -> Callable[[], None]:
        """Register a listener for optimistic state changes."""
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
    def set_cached_relay(self, port: str, relay: int, state: bool) -> None:
        """Update cached relay state without sending UDP."""
        port = port.upper()
        bit = 1 << (relay - 1)
        current = self.port_states[port]
        self.port_states[port] = current | bit if state else current & ~bit

    def relay_is_on(self, port: str, relay: int) -> bool:
        """Return whether a cached relay bit is on."""
        port = port.upper()
        bit = 1 << (relay - 1)
        return bool(self.port_states[port] & bit)

    async def async_set_relay(self, port: str, relay: int, state: bool) -> None:
        """Set one relay and send the resulting full port mask once."""
        port = port.upper()
        bit = 1 << (relay - 1)

        async with self._lock:
            current = self.port_states[port]
            next_value = current | bit if state else current & ~bit
            if next_value == current:
                return

            await self._async_send_port_locked(port, next_value)
            self.port_states[port] = next_value

        self._async_notify_listeners()

    async def async_send_port(self, port: str, value: int) -> None:
        """Send a complete port mask and update cached state."""
        port = port.upper()
        value = int(value)
        async with self._lock:
            await self._async_send_port_locked(port, value)
            self.port_states[port] = value

        self._async_notify_listeners()

    async def _async_send_port_locked(self, port: str, value: int) -> None:
        """Send one UDP packet. Caller must hold the lock."""
        packet = bytes((ord(port), value))
        _LOGGER.debug("Sending Elexol relay packet to %s:%s: %r", self.host, self.udp_port, packet)
        await self.hass.async_add_executor_job(_send_udp_packet, self.host, self.udp_port, packet)


def _send_udp_packet(host: str, udp_port: int, packet: bytes) -> None:
    """Send a UDP packet to the relay board."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(packet, (host, udp_port))
    except OSError as err:
        raise HomeAssistantError(
            f"Failed to send Elexol UDP packet to {host}:{udp_port}: {err}"
        ) from err
