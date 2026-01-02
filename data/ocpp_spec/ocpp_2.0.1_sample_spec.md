# OCPP 2.0.1 Specification - Sample / Synthetic

## Ground Fault Protection

Ground fault protection is a critical safety feature in electric vehicle charging stations. When a ground fault is detected:

1. **Detection**: The charging station continuously monitors for ground faults during charging operations
1. **Response**: Upon detection, the station must immediately stop the charging process
1. **Error Code**: GF_001 indicates ground fault protection has been activated
1. **Recovery**: Manual inspection and maintenance is required before the connector can be used again

## Connector States

OCPP defines several connector states:

- **AVAILABLE**: Ready for charging
- **OCCUPIED**: Vehicle connected but not charging
- **CHARGING**: Active charging session
- **FAULTED**: Error condition requires maintenance
- **UNAVAILABLE**: Temporarily out of service

## Thermal Protection

Charging stations implement thermal protection to prevent overheating:

- Power reduction occurs automatically when temperature thresholds are exceeded
- Typical reduction: 50% power (e.g., 7.4kW to 3.7kW)
- System returns to full power once temperature normalizes

## Security

### Secure Communication

- All communication between the charging station and the Central System MUST be secured using Transport Layer Security (TLS) v1.2 or higher.
- The charging station MUST validate the Central System's certificate to prevent man-in-the-middle attacks.

### Authentication and Authorization

- The charging station MUST support authentication via RFID, NFC, and Plug & Charge (ISO 15118).
- The Central System is responsible for authorizing charging sessions based on the user's identity and account status.

## Diagnostics

### Retrieving Logs

- The Central System can request logs from the charging station using the `GetLog` message.
- The charging station MUST provide logs in a standard format (e.g., CSV, JSON).
- The logs should include timestamps, log levels (INFO, ERROR, DEBUG), and detailed messages.

### Self-Diagnosis

- The charging station MUST perform a self-diagnosis on startup and report its status to the Central System.
- The `StatusNotification` message is used to report the status of the charging station and its connectors.

## Firmware Management

### Firmware Update Process

- The firmware update process is initiated by the Central System using the `UpdateFirmware` message.
- The charging station downloads the firmware from the specified location.
- The charging station MUST verify the integrity of the downloaded firmware using a checksum or digital signature before installation.
- The charging station reports the status of the firmware update to the Central System using the `FirmwareStatusNotification` message.

### Rollback Mechanism

- In case of a failed firmware update, the charging station SHOULD attempt to roll back to the previous stable firmware version.
- The rollback mechanism is a critical feature to ensure the availability of the charging station.
