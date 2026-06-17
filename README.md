# Elexol Relay

Home Assistant custom integration for Elexol EtherIO relay boards using the board's UDP port-mask protocol.

This integration exposes Home Assistant switch entities for relay ports `A`, `B`, and `C`. A UDP packet is sent only when a relay entity is changed in Home Assistant; it does not continuously poll or continuously retransmit relay state.

## Features

- UI-based setup through Home Assistant config flow.
- Configure the board IP address and UDP port.
- Select the available relay ports: `A`, `A/B`, or `A/B/C`.
- Creates 8 switch entities for each selected port.
- Sends the same two-byte UDP command format used by Elexol EtherIO boards:
  - byte 1: ASCII port letter, `A`, `B`, or `C`
  - byte 2: 8-bit relay mask for relays 1 through 8
- Restores Home Assistant's last known relay states on startup without sending startup packets.
- Serializes UDP writes so concurrent relay changes do not interleave.

## Important Migration Note

Only one system should send UDP commands to an Elexol relay board. If Node-RED or another controller is already commanding the board, do not enable this integration as an active controller until that other UDP sender has been disabled or migrated.

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
| Host | IP address or hostname of the Elexol EtherIO board. |
| UDP port | Destination UDP port. The default is `2424`. |
| Available ports | Which relay ports exist on the board: `A`, `A/B`, or `A/B/C`. |

Each selected port creates eight switch entities named like:

- `switch.elexol_relay_port_a_relay_1`
- `switch.elexol_relay_port_a_relay_2`
- ...
- `switch.elexol_relay_port_c_relay_8`

## How Commands Are Sent

The integration keeps an optimistic cached mask for each configured port. When one relay switch changes, the integration updates that bit in the cached mask and sends the full two-byte port command once.

For example, turning on relay `B2` sets bit 2 in port `B`'s mask and sends:

```text
0x42 <mask>
```

`0x42` is ASCII `B`.

## Limitations

- The Elexol UDP protocol used here is write-only. The integration cannot read physical relay state back from the board.
- Entity state is therefore optimistic and represents the last command Home Assistant believes it sent.
- Startup state is restored from Home Assistant's recorder and is not automatically transmitted to the board.
- If another controller also sends UDP packets, Home Assistant's entity states may not match the board.

## Releases

HACS uses GitHub Releases to detect semantic versions. This repository includes a tag-driven release workflow: pushing a tag like `v0.1.0` creates a GitHub Release using `release-notes/v0.1.0.md` when that file exists.

## Development

Run a syntax check locally with:

```bash
python3 -m py_compile custom_components/elexol_relay/*.py
```

The repository includes GitHub Actions for HACS validation and Home Assistant hassfest validation.
