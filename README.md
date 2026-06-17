# Elexol Relay

Home Assistant custom integration for Elexol Ether I/O 24 R relay boards using the board's UDP port-mask protocol.

This integration exposes Home Assistant switch entities for relay ports `A`, `B`, and `C`. A UDP write packet is sent only when a relay entity is changed in Home Assistant. The integration then reads the physical port value back from the board and uses that readback as the Home Assistant state.

## Features

- UI-based setup through Home Assistant config flow.
- Configure the board IP address, UDP port, installed relay ports, and readback polling interval.
- Select the available relay ports: `A`, `A/B`, or `A/B/C`.
- Creates 8 switch entities for each selected port.
- Writes the Elexol Ether I/O 24 R two-byte port command format:
  - byte 1: uppercase ASCII port letter, `A`, `B`, or `C`
  - byte 2: 8-bit relay mask for relays 1 through 8
- Reads relay state back using lowercase port commands: `a`, `b`, and `c`.
- Initializes Home Assistant switch states from board readback at startup.
- Verifies every write by reading the port back from the board.
- Polls configured ports periodically to detect outside changes, including during migration from Node-RED.
- Serializes UDP writes and reads so concurrent relay changes do not interleave.

## Important Migration Note

Only one system should send UDP commands to an Elexol relay board. If Node-RED or another controller is already commanding the board, do not enable this integration as an active controller until that other UDP sender has been disabled or migrated.

Readback polling can help observe outside changes while migrating, but it does not make simultaneous writers safe. If two systems send write commands, the last write wins.

## Installation With HACS

1. In HACS, open **Integrations**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add `https://github.com/rvdbijl/hacs-elexol-relay` as an **Integration** repository.
4. Install **Elexol Relay**.
5. Restart Home Assistant.
6. Go to **Settings -> Devices & services -> Add integration** and search for **Elexol Relay**.

## Manual Installation

Copy `custom_components/elexol_relay` into your Home Assistant `custom_components` directory, then restart Home Assistant.

## Configuration

The setup flow asks for:

| Field | Description |
| --- | --- |
| Host | IP address or hostname of the Elexol Ether I/O 24 R board. |
| UDP port | Destination UDP port. The default is `2424`. |
| Installed relay ports | Which relay ports exist on the board: `A`, `A/B`, or `A/B/C`. |
| Readback poll interval seconds | How often to read configured port states from the board. Default is `30`; set to `0` to disable background polling. Startup reads and write verification still run. |

Each selected port creates eight switch entities named like:

- `switch.elexol_relay_port_a_relay_1`
- `switch.elexol_relay_port_a_relay_2`
- ...
- `switch.elexol_relay_port_c_relay_8`

## How Commands Are Sent And Verified

When one relay switch changes, the integration updates that bit in the cached mask, sends the full uppercase port write command once, then sends the lowercase read command for that same port.

For example, turning on relay `B2` sets bit 2 in port `B`'s mask and writes:

```text
0x42 <mask>
```

`0x42` is ASCII `B`.

The integration then reads port `B` with:

```text
0x62
```

`0x62` is ASCII `b`. The switch entities are updated from the board's returned port value. If the readback does not match the command, Home Assistant raises a service error and the affected switch entities keep the readback state.

## Diagnostics

Each switch exposes diagnostic attributes:

- `port`: Elexol port letter.
- `relay`: relay number within the port.
- `port_value`: last readback byte for the port.
- `readback_verified`: whether the last write verification for that port succeeded.
- `last_read_error`: latest board communication or verification error.

If the board does not respond to startup reads or polling, the entities are marked unavailable until a later read succeeds.

## Limitations

- Readback confirms the Elexol output port value, not the physical position of a damper or the mechanical state of equipment connected downstream.
- UDP has no delivery guarantee. The write-then-readback cycle greatly improves confidence, but a missing response still means the current physical board state is unknown.
- If another controller also sends UDP packets, Home Assistant will update to whatever the board reports during polling, but simultaneous writers can still fight each other.

## Releases

HACS uses GitHub Releases to detect semantic versions. This repository includes a tag-driven release workflow: pushing a tag like `v0.2.0` creates a GitHub Release using `release-notes/v0.2.0.md` when that file exists.

## Development

Run a syntax check locally with:

```bash
python3 -m py_compile custom_components/elexol_relay/*.py
```

The repository includes GitHub Actions for HACS validation and Home Assistant hassfest validation.
