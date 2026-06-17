"""Switch platform for Elexol Relay."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import ElexolRelayHub


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Elexol relay switches."""
    hub: ElexolRelayHub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ElexolRelaySwitch(entry, hub, port, relay)
            for port in hub.ports
            for relay in range(1, 9)
        ]
    )


class ElexolRelaySwitch(SwitchEntity):
    """Representation of one Elexol relay output."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, hub: ElexolRelayHub, port: str, relay: int) -> None:
        """Initialize the relay switch."""
        self._entry = entry
        self._hub = hub
        self._port = port
        self._relay = relay
        self._remove_listener: Callable[[], None] | None = None

        self._attr_name = f"Port {port} Relay {relay}"
        self._attr_icon = "mdi:electric-switch"
        self._attr_unique_id = f"{entry.entry_id}_{port.lower()}_{relay}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Elexol",
            model="Ether I/O 24 R",
            name=f"Elexol Relay {entry.data[CONF_HOST]}",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def available(self) -> bool:
        """Return whether the relay board is responding to readback."""
        return self._hub.available

    @property
    def is_on(self) -> bool:
        """Return true if the last board readback says this relay bit is on."""
        return self._hub.relay_is_on(self._port, self._relay)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic readback attributes."""
        return {
            "port": self._port,
            "relay": self._relay,
            "port_value": self._hub.port_value(self._port),
            "readback_verified": self._hub.port_verified(self._port),
            "last_read_error": self._hub.last_error,
        }

    async def async_added_to_hass(self) -> None:
        """Register for hub readback updates."""
        self._remove_listener = self._hub.async_add_listener(self._handle_hub_update)
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Remove hub listener."""
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the relay on."""
        await self._hub.async_set_relay(self._port, self._relay, True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the relay off."""
        await self._hub.async_set_relay(self._port, self._relay, False)

    @callback
    def _handle_hub_update(self) -> None:
        """Write switch state after board readback changes."""
        self.async_write_ha_state()
