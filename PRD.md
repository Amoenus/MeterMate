# Product Design & Requirements Document: MeterMate

Author: Amoenus
Version: 1.0
Date: June 16, 2025
Status: Draft

1. Introduction & Problem Statement
   Home Assistant's Energy Dashboard is a powerful tool for visualising energy consumption, but it primarily relies on real-time data from smart meters or power-monitoring devices. A significant portion of users do not have access to these devices and instead receive periodic utility bills (e.g., monthly) with total consumption figures, or they take manual readings from older, cumulative meters.

Currently, there is no straightforward, user-friendly way to input this periodic or point-in-time data into Home Assistant to make it compatible with the Energy Dashboard's long-term statistics. Existing workarounds involve complex template sensor configurations, manual database adjustments, or calling developer services, which are non-obvious and intimidating for the average user.

This project aims to solve this problem by providing a simple, dedicated integration for manually adding utility readings.

2. Goals & Objectives
   The primary goal is to empower any Home Assistant user, regardless of their technical skill, to accurately track historical and ongoing utility consumption using manual data entry.

Key Objectives for MVP (Minimum Viable Product):

Create a simple and intuitive setup process via the UI (Config Flow).

Provide a robust backend service for adding data that is safe and compliant with Home Assistant's architecture.

Generate a sensor entity that is immediately compatible with the Energy Dashboard.

Offload the complexity of data parsing and conversion from the user to the integration.

Serve as a simple, reliable alternative to complex template-based workarounds.

3. Target Audience
   Home Assistant users with "dumb" utility meters (electricity, gas, water) who perform manual readings.

Users who receive monthly/quarterly bills with a total consumption figure for the period.

Users who are new to Home Assistant and find the current manual entry methods overly complex.

4. User Scenarios / Use Cases (MVP)
   Initial Setup: A new user, Jane, has a traditional electricity meter. She installs the "Manual Meter" integration. Through the UI, she creates a new sensor called "Grid Electricity", sets the unit to kWh, and enters the meter's current reading (e.g., 15432) as the "Initial Reading" so her tracking starts from zero.

Point-in-Time Reading: A month later, Jane reads her meter. The new value is 15650. She goes to a dashboard card, enters 15650 into a field, and clicks "Submit". The integration automatically calculates the consumption for the period and updates the sensor.grid_electricity total. The Energy Dashboard graph updates accordingly.

Periodic Bill Entry: John receives a bill stating he used 210 kWh from May 1st to May 31st. He uses a dashboard card, selects "Periodic Entry" mode, enters the start and end dates, puts 210 in the value field, and clicks "Submit". The integration adds this consumption to the previous total and correctly attributes it to the May period in the Energy Dashboard.

5. Feature Specifications (MVP)
   5.1. Configuration Flow (UI Setup)
   The integration will be configured via the UI. When a user adds a "Manual Meter", they will configure the following:

Name: A user-defined friendly name (e.g., "Monthly Gas Bill"). This will become the sensor name.

Unit of Measurement: A dropdown or text field for the unit (e.g., kWh, m³, gal).

Device Class: A dropdown to select the appropriate class (energy, gas, water, volume, etc.).

Initial Meter Reading (Offset): An optional number field. This is for users with existing cumulative meters. The value entered here will be subtracted from all future readings to calculate consumption since the start of tracking. Defaults to 0.

5.2. Sensor Entity
The integration will create a single sensor entity for each meter configured. This sensor will have the necessary attributes to be immediately compatible with the Energy Dashboard:

device_class: Set from the config flow (e.g., energy).

state_class: Hardcoded to total_increasing.

unit_of_measurement: Set from the config flow (e.g., kWh).

The sensor's state will be the calculated running total consumption.

5.3. Service: manual_meter.add_reading
This will be the core service that adds data. It will accept the following parameters:

entity_id: The target manual meter sensor.

value: The numeric value being entered.

mode (Optional): A selector for "Cumulative" or "Periodic". Defaults to "Cumulative".

timestamp (Optional): The date/time for a "Cumulative" reading. Defaults to now().

start_date & end_date (Optional): The date range for a "Periodic" reading.

Backend Logic: The service will contain the logic to convert the input into a single (timestamp, total_cumulative_value) data point to be imported into the statistics table.

5.4. Frontend UI (MVP)
For the MVP, we will not build a custom Lovelace card. Instead, the documentation will guide the user to create a simple and effective UI using the standard Entities Card, combining the input_number helper and a script that calls the new service, as prototyped in our discussion.

6. Out of Scope for MVP
   A custom Lovelace card for data entry.

Automatic parsing of any file type (XML, PDF, etc.).

Editing or deleting previously entered data points via the UI.

Handling of multiple tariffs.

Automatic cost calculation (this should be handled by the Energy Dashboard itself).

8. Implementation Strategy

8.1. Database Schema Understanding
Based on successful implementations, we need to interact with:

```sql
-- Statistics metadata table
CREATE TABLE statistics_meta (
    id INTEGER PRIMARY KEY,
    statistic_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    unit_of_measurement TEXT,
    has_mean BOOLEAN,
    has_sum BOOLEAN,
    name TEXT
);

-- Long-term statistics table
CREATE TABLE statistics (
    id INTEGER PRIMARY KEY,
    metadata_id INTEGER REFERENCES statistics_meta(id),
    start_ts REAL NOT NULL,
    state REAL,
    sum REAL,
    created_ts REAL DEFAULT (strftime('%s', 'now'))
);
```

8.2. Data Processing Flow
1. **Metadata Creation**: Ensure sensor exists in `statistics_meta` table
2. **Timestamp Conversion**: Convert user-provided dates to Unix epoch timestamps
3. **Data Validation**: Prevent duplicate entries and validate data ranges
4. **Direct Insertion**: Insert with correct historical timestamps into `statistics` table
5. **State Update**: Update current sensor state if data is more recent

8.3. Historical Data Handling
- **Cumulative Mode**: Convert meter readings to total consumption using initial reading offset
- **Periodic Mode**: Distribute consumption across the specified date range
- **Timestamp Alignment**: Align timestamps to hourly boundaries for optimal Energy Dashboard compatibility
- **Gap Handling**: Handle data gaps intelligently without overwriting existing Home Assistant data

8.4. Safety Measures
- **Backup Strategy**: Recommend database backups before bulk imports
- **Rollback Capability**: Ability to identify and remove imported data if needed
- **Validation**: Extensive validation of input data and database state
- **Logging**: Comprehensive logging for troubleshooting and audit trails

9. Technical Approach
   The integration will be built as a standard Home Assistant custom component.

Initial Proof of Concept Status:
We have a working PoC that successfully creates sensors and allows data entry through services. However, the current implementation has a critical limitation: it logs all data at the current timestamp rather than at the correct historical dates. This prevents proper historical tracking in the Energy Dashboard.

Revised Technical Approach:
After researching successful implementations (such as the Home-Assistant-Import-Energy-Data project), it's clear that achieving true historical data logging requires direct database manipulation rather than relying on Home Assistant's built-in statistics APIs. The built-in APIs are designed for real-time data ingestion and don't properly handle backdated entries.

Core Requirements for Historical Data:
1. **Direct Database Access**: We need to directly insert data into Home Assistant's `statistics` and `statistics_short_term` tables with correct timestamps
2. **Unix Timestamp Conversion**: All timestamps must be converted to Unix epoch format for proper database storage
3. **Proper Table Structure**: Understanding and respecting Home Assistant's database schema (tested with schema version 50+)
4. **Metadata Handling**: Ensuring proper `statistics_meta` entries exist for our sensors
5. **Data Validation**: Ensuring data integrity and handling of duplicate entries

Database Tables Involved:
- `statistics_meta`: Contains sensor metadata (statistic_id, unit_of_measurement, source)
- `statistics`: Long-term statistics data (metadata_id, state, sum, start_ts, created_ts)
- `statistics_short_term`: Short-term statistics data for recent data

The integration's sensor will continue to track current state, but historical data will be inserted directly into the statistics tables with the correct timestamps, ensuring full compatibility with the Energy Dashboard's historical views.
