# Changelog

## v0.2.0

- Add Ether I/O 24 R readback support using lowercase port commands.
- Initialize switch states from board readback instead of restored Home Assistant state.
- Verify each relay write by reading the affected port back from the board.
- Add configurable readback polling interval, with `0` disabling background polling.
- Add switch diagnostic attributes for port value, verification status, and last read error.

## v0.1.0 - 2026-06-17

- Initial HACS-compatible release.
- Add UI config flow for host, UDP port, and available port selection.
- Add switch entities for selected Elexol relay ports.
- Send one UDP port-mask command when a relay entity changes state.
- Add HACS validation, hassfest validation, and tag-based GitHub release workflow.
