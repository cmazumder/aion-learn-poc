# Firmware Update Process

## Introduction

This document outlines the standard operating procedure for updating the firmware on our charging stations. It is important to follow these steps carefully to ensure a successful update and to minimize downtime.

## Pre-Update Checklist

1. **Verify Firmware Integrity:** Before initiating an update, ensure that the firmware binary has been verified with its checksum (MD5 or SHA256).
1. **Check Station Status:** Ensure that the charging station is online and not in an error state.
1. **Schedule a Maintenance Window:** If possible, schedule the firmware update during off-peak hours to minimize disruption to users.
1. **Review Release Notes:** Carefully read the release notes for the new firmware version to understand the changes and any potential impact.

## Update Procedure

1. **Initiate Update:** Use the Central System to initiate the firmware update by sending the `UpdateFirmware` command to the charging station.
1. **Monitor Progress:** Monitor the progress of the firmware update using the `FirmwareStatusNotification` messages from the station. The station will report its status as `Downloading`, `Downloaded`, `Installing`, and finally `InstallationFailed` or `Installed`.
1. **Verify Installation:** Once the station reports `Installed`, verify that the new firmware version is reported in the station's `BootNotification`.

## Rollback Procedure

In the event of a failed firmware update, the station should automatically roll back to the previous version. If the station does not come back online after a failed update, please follow these steps:

1. **Attempt a Remote Reboot:** A remote reboot can sometimes resolve issues with a failed update.
1. **Dispatch a Technician:** If a remote reboot does not work, a technician must be dispatched to the site to perform a manual rollback or to re-flash the firmware.
1. **Create a JIRA Ticket:** Create a JIRA ticket with the "Firmware Update Failed" category, and include the station ID, the firmware versions involved, and any available logs.
