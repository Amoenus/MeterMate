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
   The integration will be built as a standard Home Assistant custom component with a sophisticated data management interface.

Evolution to Comprehensive Manual Data Entry Platform:
MeterMate evolves from basic service calls to become a full-featured data source for Home Assistant's Energy Dashboard. The value this integration adds is:

1. **Complete CRUD Interface**: Full Create, Read, Update, Delete capabilities for manual utility readings
2. **Dedicated Data Source**: Acts as a standalone data source specifically for manual utility bill and meter reading data
3. **Energy Dashboard Integration**: Seamlessly exposes data to Home Assistant's Energy Dashboard as if it were a smart meter
4. **User-Friendly Management**: Intuitive interface for managing historical and ongoing utility consumption data
5. **Data Integrity**: Maintains data consistency and provides validation for all manual entries

9.1. Database Architecture with SQLAlchemy
Home Assistant uses SQLAlchemy 2.0+ as its Object Relational Mapper (ORM). Our implementation will:

- **Leverage Existing Models**: Use Home Assistant's existing SQLAlchemy models for statistics where available
- **Extend with Custom Models**: Create MeterMate-specific models that integrate seamlessly with Home Assistant's schema
- **Maintain Compatibility**: Ensure all operations are compatible with Home Assistant's database migrations and schema evolution

Key Benefits of SQLAlchemy Integration:
- **Type Safety**: Strong typing with modern SQLAlchemy 2.0 features
- **Database Portability**: Support for SQLite, PostgreSQL, MySQL through SQLAlchemy
- **Transaction Management**: Proper ACID compliance with rollback capabilities
- **Migration Support**: Schema versioning and automatic migration handling
- **Performance**: Optimized queries and connection pooling

9.2. Data Management API Structure
```python
class MeterMateDataManager:
    """Full CRUD data management interface for MeterMate utility readings."""
    
    # CREATE operations
    async def add_reading(self, entity_id: str, reading: Reading) -> OperationResult
    async def bulk_import(self, entity_id: str, readings: List[Reading]) -> BulkResult
    
    # READ operations
    async def get_reading(self, reading_id: str) -> Reading | None
    async def get_readings(self, entity_id: str, period: TimePeriod) -> List[Reading]
    async def get_all_readings(self, entity_id: str) -> List[Reading]
    
    # UPDATE operations
    async def update_reading(self, reading_id: str, reading: Reading) -> OperationResult
    async def bulk_update(self, updates: List[ReadingUpdate]) -> BulkResult
    
    # DELETE operations
    async def delete_reading(self, reading_id: str) -> OperationResult
    async def delete_readings(self, entity_id: str, period: TimePeriod) -> OperationResult
    async def bulk_delete(self, reading_ids: List[str]) -> BulkResult
    
    # VALIDATION and UTILITY
    async def validate_data(self, readings: List[Reading]) -> ValidationResult
    async def recalculate_statistics(self, entity_id: str) -> OperationResult
```

9.3. Enhanced Database Models
```python
from homeassistant.components.recorder import db_schema
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey

class MeterMateReading(db_schema.Base):
    """Model for storing MeterMate readings with full audit trail."""
    __tablename__ = "metermate_readings"
    
    id = Column(Integer, primary_key=True)
    entity_id = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)
    reading_type = Column(String, nullable=False)  # cumulative, periodic
    operation_id = Column(String, nullable=False)  # for rollback tracking
    created_at = Column(DateTime, default=func.now())
    
    # Relationship to Home Assistant's statistics
    statistics = relationship("Statistics", back_populates="metermate_readings")
```

9.4. Core Requirements for Historical Data (Updated):
1. **SQLAlchemy ORM Integration**: Use Home Assistant's SQLAlchemy session and models
2. **Proper Transaction Management**: Ensure ACID compliance with proper rollback capabilities  
3. **Home Assistant Schema Compatibility**: Respect existing `statistics_meta`, `statistics`, and `statistics_short_term` table structures
4. **Audit Trail**: Complete tracking of all data operations for troubleshooting and rollback
5. **Data Validation**: Comprehensive validation before database operations
6. **Bulk Operations**: Efficient handling of large data imports
7. **Migration Support**: Forward-compatible database schema design

9.5. Implementation Phases:
**Phase 1**: Replace direct SQLite operations with SQLAlchemy ORM
**Phase 2**: Implement advanced data management interface
**Phase 3**: Add bulk import and export capabilities  
**Phase 4**: Implement comprehensive audit trail and rollback features
**Phase 5**: Create management UI components for advanced operations

Database Tables Involved:
- `statistics_meta`: Contains sensor metadata (using Home Assistant's existing model)
- `statistics`: Long-term statistics data (using Home Assistant's existing model)
- `statistics_short_term`: Short-term statistics data (using Home Assistant's existing model)
- `metermate_readings`: New audit table for MeterMate-specific operations
- `metermate_operations`: New table for tracking bulk operations and rollbacks

The integration will provide both backward compatibility with the existing service interface and new advanced data management capabilities through a rich API that other integrations can also leverage.
