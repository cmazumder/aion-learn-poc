# Release Notes - v2.5.0

## New Features

- **Enhanced Diagnostics**: Added full support for the OCPP 2.0.1 `GetLog` message. This allows the Central System to remotely fetch detailed diagnostic logs from stations, significantly improving remote troubleshooting capabilities.

## Bug Fixes

- **Legacy Station Compatibility**: Resolved an issue where stations with older `legacy_cpnk` board configurations were failing to report `MeterValues` after a session. The system now correctly identifies the board type and uses the appropriate data format.
- **UI**: Fixed a minor display issue on the analytics dashboard where charts would not render if a directory summary was empty.