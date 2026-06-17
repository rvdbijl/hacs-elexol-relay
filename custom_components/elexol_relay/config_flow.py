"""Config flow for Elexol Relay."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_POLL_INTERVAL,
    CONF_PORT_SELECTION,
    CONF_PORTS,
    CONF_UDP_PORT,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT_SELECTION,
    DEFAULT_UDP_PORT,
    DOMAIN,
    PORT_SELECTION_OPTIONS,
    PORT_SELECTIONS,
)


def _ports_from_selection(selection: str) -> list[str]:
    """Return relay ports for an installed-port selection."""
    return list(PORT_SELECTIONS.get(selection, PORT_SELECTIONS[DEFAULT_PORT_SELECTION]))


def _selection_from_ports(ports: list[str]) -> str:
    """Return the installed-port selection matching stored ports."""
    normalized = tuple(ports)
    for selection, selection_ports in PORT_SELECTIONS.items():
        if normalized == selection_ports:
            return selection
    return DEFAULT_PORT_SELECTION


def _poll_interval_validator(value: Any) -> int:
    """Validate poll interval seconds. Zero disables polling."""
    try:
        value = int(value)
    except (TypeError, ValueError) as err:
        raise vol.Invalid("poll interval must be a number of seconds") from err
    if value < 0 or value > 3600:
        raise vol.Invalid("poll interval must be between 0 and 3600 seconds")
    return value


def _config_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the initial config flow schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(
                CONF_UDP_PORT,
                default=defaults.get(CONF_UDP_PORT, DEFAULT_UDP_PORT),
            ): cv.port,
            vol.Required(
                CONF_PORT_SELECTION,
                default=defaults.get(CONF_PORT_SELECTION, DEFAULT_PORT_SELECTION),
            ): vol.In(PORT_SELECTION_OPTIONS),
            vol.Required(
                CONF_POLL_INTERVAL,
                default=defaults.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
            ): _poll_interval_validator,
        }
    )


def _options_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the options flow schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_UDP_PORT,
                default=defaults.get(CONF_UDP_PORT, DEFAULT_UDP_PORT),
            ): cv.port,
            vol.Required(
                CONF_PORT_SELECTION,
                default=defaults.get(CONF_PORT_SELECTION, DEFAULT_PORT_SELECTION),
            ): vol.In(PORT_SELECTION_OPTIONS),
            vol.Required(
                CONF_POLL_INTERVAL,
                default=defaults.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
            ): _poll_interval_validator,
        }
    )


class ElexolRelayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Elexol Relay config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            port_selection = user_input[CONF_PORT_SELECTION]
            host = user_input[CONF_HOST].strip()
            if not host:
                errors[CONF_HOST] = "host_required"
            else:
                udp_port = int(user_input[CONF_UDP_PORT])
                await self.async_set_unique_id(f"{host}:{udp_port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Elexol Relay {host}",
                    data={
                        CONF_HOST: host,
                        CONF_UDP_PORT: udp_port,
                        CONF_PORT_SELECTION: port_selection,
                        CONF_PORTS: _ports_from_selection(port_selection),
                        CONF_POLL_INTERVAL: int(user_input[CONF_POLL_INTERVAL]),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_config_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Create the options flow."""
        return ElexolRelayOptionsFlow(config_entry)


class ElexolRelayOptionsFlow(config_entries.OptionsFlow):
    """Handle Elexol Relay options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage options."""
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}
        current.setdefault(
            CONF_PORT_SELECTION,
            _selection_from_ports(
                current.get(CONF_PORTS, list(PORT_SELECTIONS[DEFAULT_PORT_SELECTION]))
            ),
        )
        current.setdefault(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

        if user_input is not None:
            port_selection = user_input[CONF_PORT_SELECTION]
            return self.async_create_entry(
                title="",
                data={
                    CONF_UDP_PORT: int(user_input[CONF_UDP_PORT]),
                    CONF_PORT_SELECTION: port_selection,
                    CONF_PORTS: _ports_from_selection(port_selection),
                    CONF_POLL_INTERVAL: int(user_input[CONF_POLL_INTERVAL]),
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current),
            errors=errors,
        )
