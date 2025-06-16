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

7. Technical Approach
   The integration will be built as a standard Home Assistant custom component. The core logic for data insertion will leverage the internal homeassistant.components.recorder.statistics.async_import_statistics function. This is the officially sanctioned, though not publicly documented, method for inserting historical statistics and ensures compatibility with the database structure without resorting to direct SQL manipulation.

The integration's sensor will get its state from the statistics table, ensuring that its value is always consistent with the long-term data used by the Energy Dashboard.
