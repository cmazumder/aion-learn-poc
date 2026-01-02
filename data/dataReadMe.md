# Synthetic Data README

This document provides a summary of the synthetic data used in this project and contains sample questions that can be used to evaluate the RAG system.

This file should **not** be ingested into the vector database.

______________________________________________________________________

## Data Directory Cheatsheet

- **`ocpp_spec/`**

  - **Content:** Contains the Open Charge Point Protocol (OCPP) specification documents in Markdown format.
  - **Purpose:** Provides the technical specifications for the communication protocol between charging stations and the central management system.

- **`sample_jira/`**

  - **Content:** Contains sample JIRA tickets in JSON format, mimicking the structure of the JIRA API.
  - **Purpose:** Provides realistic examples of charging station issues as they would be tracked in JIRA.

- **`sample_confluence/`**

  - **Content:** Contains sample Confluence pages in Markdown format.
  - **Purpose:** Provides examples of troubleshooting guides and process documents that would be stored in Confluence.

- **`sample_logs/`**

  - **Content:** Contains sample log files from charging sessions.
  - **Purpose:** Provides examples of the raw log data that can be used for root cause analysis.

______________________________________________________________________

## Cross-Domain Sample Questions for RAG Evaluation

### Developer Use Case: Correlating a Jira Ticket with a Git PR

**Scenario**: A developer is trying to understand a recent change to the authentication backend and wants to know the full story behind it.

> **Query**: "I'm looking at Jira ticket CO-127 about a race condition. Can you explain the fix that was implemented in PR #4567 and how it affects the `api_key_from_machine_id` method in the `SpoolerVaultAuth` class?"

______________________________________________________________________

### QA Engineer Use Case: Correlating Release Notes, DB Exports, and Specs

**Scenario**: A QA engineer needs to validate a bug fix mentioned in the latest release notes and wants to identify a suitable test device and the correct diagnostic procedure.

> **Query**: "I need to test the `legacy_cpnk` bug fix mentioned in release notes v2.5.0. According to the `stations_config.csv` database export, which station should I use for testing? Also, what is the OCPP 2.0.1 `GetLog` message format I should expect to use for diagnostics?"

______________________________________________________________________
