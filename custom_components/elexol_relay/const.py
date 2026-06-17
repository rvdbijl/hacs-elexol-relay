"""Constants for the Elexol Relay integration."""

from homeassistant.const import Platform

DOMAIN = "elexol_relay"

CONF_PORTS = "ports"
CONF_PORT_SELECTION = "port_selection"
CONF_UDP_PORT = "udp_port"

DEFAULT_UDP_PORT = 2424
PORTS = ("A", "B", "C")
PORT_SELECTION_A = "A"
PORT_SELECTION_AB = "A/B"
PORT_SELECTION_ABC = "A/B/C"
DEFAULT_PORT_SELECTION = PORT_SELECTION_ABC
PORT_SELECTIONS = {
    PORT_SELECTION_A: ("A",),
    PORT_SELECTION_AB: ("A", "B"),
    PORT_SELECTION_ABC: ("A", "B", "C"),
}
PORT_SELECTION_OPTIONS = {
    PORT_SELECTION_A: "Port A",
    PORT_SELECTION_AB: "Ports A and B",
    PORT_SELECTION_ABC: "Ports A, B, and C",
}

PLATFORMS = [Platform.SWITCH]
