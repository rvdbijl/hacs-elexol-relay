"""The Elexol Relay integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import CONF_PORTS, CONF_UDP_PORT, DEFAULT_UDP_PORT, DOMAIN, PLATFORMS, PORTS
from .hub import ElexolRelayHub


def _entry_value(entry: ConfigEntry, key: str, default=None):
    """Return an option value, falling back to config entry data."""
    return entry.options.get(key, entry.data.get(key, default))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Elexol Relay from a config entry."""
    ports = list(_entry_value(entry, CONF_PORTS, list(PORTS)))
    hub = ElexolRelayHub(
        hass=hass,
        host=entry.data[CONF_HOST],
        udp_port=int(_entry_value(entry, CONF_UDP_PORT, DEFAULT_UDP_PORT)),
        ports=ports,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Elexol Relay config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
