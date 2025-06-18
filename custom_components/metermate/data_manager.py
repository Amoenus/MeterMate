"""Data management interface for MeterMate."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.helpers import storage
from homeassistant.util import dt as dt_util

from .const import ATTR_INTEGRATION_NAME
from .database import HistoricalDataHandler
from .models import OperationResult, Reading, ValidationResult

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = f"{ATTR_INTEGRATION_NAME}_readings"

# State management constants
MINIMUM_STATE_CHANGE = 0.1  # Minimum change to record new state
DAILY_STATE_INTERVAL = 86400  # Seconds in a day for daily snapshots


@dataclass
class TimePeriod:
    """Time period for querying readings."""

    start: datetime
    end: datetime


class MeterMateDataManager:
    """Full CRUD data management interface for MeterMate utility readings."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the data manager."""
        self.hass = hass
        self._store = storage.Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, list[Reading]] = {}
        self._loaded = False
        self._historical_handler = HistoricalDataHandler(hass)

    async def async_load(self) -> None:
        """Load stored data."""
        if self._loaded:
            return

        stored_data = await self._store.async_load()
        if stored_data:
            # Convert stored data back to Reading objects
            for entity_id, readings_data in stored_data.items():
                self._data[entity_id] = [
                    Reading.from_dict(reading_data) for reading_data in readings_data
                ]

        self._loaded = True

    async def async_save(self) -> None:
        """Save data to storage."""
        # Convert Reading objects to dictionaries for storage
        data_to_store = {}
        for entity_id, readings in self._data.items():
            data_to_store[entity_id] = [reading.to_dict() for reading in readings]

        await self._store.async_save(data_to_store)

    # CREATE operations
    async def add_reading(self, entity_id: str, reading: Reading) -> OperationResult:
        """Add a single reading."""
        await self.async_load()

        # Validate the reading
        validation = await self.validate_reading(reading)
        if not validation.is_valid:
            return OperationResult(
                success=False,
                message=f"Validation failed: {', '.join(validation.errors)}",
            )

        # Add to internal storage
        if entity_id not in self._data:
            self._data[entity_id] = []

        # Check for duplicates
        existing = await self.get_reading_by_timestamp(entity_id, reading.timestamp)
        if existing:
            return OperationResult(
                success=False,
                message=(
                    f"Reading already exists for timestamp {reading.timestamp}. "
                    f"Existing reading: {existing.value} {existing.unit}. "
                    f"Use update_reading service to modify existing readings."
                ),
            )

        # Generate ID if not provided
        if not reading.id:
            reading.id = str(uuid4())

        self._data[entity_id].append(reading)

        # Sort readings by timestamp
        self._data[entity_id].sort(key=lambda r: r.timestamp)

        # Save to storage
        await self.async_save()

        # Update Home Assistant statistics
        await self._update_statistics(entity_id)

        # Inject historical data directly into Home Assistant recorder
        await self._inject_historical_data(entity_id, reading)

        # NOTE: We intentionally do NOT update the sensor value here
        # to avoid creating a "journey" of state changes in HA history.
        # The sensor will get the latest value via its async_update method.

        _LOGGER.info(
            "Added reading for %s: %s %s at %s",
            entity_id,
            reading.value,
            reading.unit,
            reading.timestamp,
        )

        return OperationResult(
            success=True,
            message="Reading added successfully",
            data={"reading_id": reading.id},
        )

    async def bulk_import(
        self, entity_id: str, readings: list[Reading]
    ) -> dict[str, Any]:
        """Import multiple readings at once."""
        await self.async_load()

        results = {
            "success_count": 0,
            "error_count": 0,
            "errors": [],
            "reading_ids": [],
        }

        for reading in readings:
            result = await self.add_reading(entity_id, reading)
            if result.success:
                results["success_count"] += 1
                if result.data and "reading_id" in result.data:
                    results["reading_ids"].append(result.data["reading_id"])
            else:
                results["error_count"] += 1
                results["errors"].append(
                    {
                        "timestamp": reading.timestamp.isoformat(),
                        "error": result.message,
                    }
                )

        return results

    # READ operations
    async def get_reading(self, entity_id: str, reading_id: str) -> Reading | None:
        """Get a specific reading by ID."""
        await self.async_load()

        if entity_id not in self._data:
            return None

        for reading in self._data[entity_id]:
            if reading.id == reading_id:
                return reading

        return None

    async def get_reading_by_timestamp(
        self, entity_id: str, timestamp: datetime
    ) -> Reading | None:
        """Get a reading by timestamp."""
        await self.async_load()

        if entity_id not in self._data:
            return None

        for reading in self._data[entity_id]:
            if reading.timestamp == timestamp:
                return reading

        return None

    async def get_readings(
        self, entity_id: str, period: TimePeriod | None = None
    ) -> list[Reading]:
        """Get readings for an entity, optionally filtered by time period."""
        await self.async_load()

        if entity_id not in self._data:
            return []

        readings = self._data[entity_id]

        if period:
            readings = [
                r for r in readings if period.start <= r.timestamp <= period.end
            ]

        return sorted(readings, key=lambda r: r.timestamp)

    async def get_all_readings(self, entity_id: str) -> list[Reading]:
        """Get all readings for an entity."""
        return await self.get_readings(entity_id)

    async def get_reading_count(self, entity_id: str) -> int:
        """Get the total number of readings for an entity."""
        await self.async_load()

        if entity_id not in self._data:
            return 0

        return len(self._data[entity_id])

    async def get_latest_reading(self, entity_id: str) -> Reading | None:
        """Get the most recent reading for an entity."""
        readings = await self.get_all_readings(entity_id)
        if not readings:
            return None

        return max(readings, key=lambda r: r.timestamp)

    async def get_earliest_reading(self, entity_id: str) -> Reading | None:
        """Get the oldest reading for an entity."""
        readings = await self.get_all_readings(entity_id)
        if not readings:
            return None

        return min(readings, key=lambda r: r.timestamp)

    # UPDATE operations
    async def update_reading(
        self, entity_id: str, reading_id: str, updated_reading: Reading
    ) -> OperationResult:
        """Update an existing reading."""
        await self.async_load()

        if entity_id not in self._data:
            return OperationResult(success=False, message="Entity not found")

        # Find the reading to update
        for i, reading in enumerate(self._data[entity_id]):
            if reading.id == reading_id:
                # Validate the updated reading
                validation = await self.validate_reading(updated_reading)
                if not validation.is_valid:
                    return OperationResult(
                        success=False,
                        message=f"Validation failed: {', '.join(validation.errors)}",
                    )

                # Keep the original ID
                updated_reading.id = reading_id
                self._data[entity_id][i] = updated_reading

                # Re-sort readings by timestamp
                self._data[entity_id].sort(key=lambda r: r.timestamp)

                # Save to storage
                await self.async_save()

                # Update Home Assistant statistics
                await self._update_statistics(entity_id)

                # NOTE: Not updating sensor value to avoid state change journey

                _LOGGER.info("Updated reading %s for %s", reading_id, entity_id)

                return OperationResult(
                    success=True, message="Reading updated successfully"
                )

        return OperationResult(success=False, message="Reading not found")

    # DELETE operations
    async def delete_reading(self, entity_id: str, reading_id: str) -> OperationResult:
        """Delete a specific reading."""
        await self.async_load()

        if entity_id not in self._data:
            return OperationResult(success=False, message="Entity not found")

        # Find and remove the reading
        for i, reading in enumerate(self._data[entity_id]):
            if reading.id == reading_id:
                removed_reading = self._data[entity_id].pop(i)

                # Save to storage
                await self.async_save()

                # Update Home Assistant statistics
                await self._update_statistics(entity_id)

                # NOTE: Not updating sensor value to avoid state change journey

                _LOGGER.info(
                    "Deleted reading %s for %s (value: %s at %s)",
                    reading_id,
                    entity_id,
                    removed_reading.value,
                    removed_reading.timestamp,
                )

                return OperationResult(
                    success=True, message="Reading deleted successfully"
                )

        return OperationResult(success=False, message="Reading not found")

    async def delete_readings_in_period(
        self, entity_id: str, period: TimePeriod
    ) -> OperationResult:
        """Delete all readings in a time period."""
        await self.async_load()

        if entity_id not in self._data:
            return OperationResult(success=False, message="Entity not found")

        # Find readings in the period
        readings_to_remove = [
            r
            for r in self._data[entity_id]
            if period.start <= r.timestamp <= period.end
        ]

        if not readings_to_remove:
            return OperationResult(
                success=True, message="No readings found in the specified period"
            )

        # Remove the readings
        self._data[entity_id] = [
            r
            for r in self._data[entity_id]
            if not (period.start <= r.timestamp <= period.end)
        ]

        # Save to storage
        await self.async_save()

        # Update Home Assistant statistics
        await self._update_statistics(entity_id)

        # Regenerate all historical data after deletion
        await self._regenerate_historical_data(entity_id)

        _LOGGER.info(
            "Deleted %d readings for %s in period %s to %s",
            len(readings_to_remove),
            entity_id,
            period.start,
            period.end,
        )

        return OperationResult(
            success=True,
            message=f"Deleted {len(readings_to_remove)} readings",
            data={"deleted_count": len(readings_to_remove)},
        )

    # VALIDATION and UTILITY
    async def validate_reading(self, reading: Reading) -> ValidationResult:
        """Validate a reading."""
        errors = []

        # Check required fields
        if reading.value is None:
            errors.append("Value is required")

        if reading.timestamp is None:
            errors.append("Timestamp is required")

        # Check timestamp is not in the future
        # Ensure we're comparing timezone-aware datetimes
        timestamp_utc = dt_util.as_utc(reading.timestamp)
        now_utc = dt_util.utcnow()
        if timestamp_utc > now_utc:
            errors.append("Timestamp cannot be in the future")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    async def recalculate_statistics(self, entity_id: str) -> OperationResult:
        """Recalculate and update statistics for an entity."""
        try:
            await self._update_statistics(entity_id)
            # Regenerate historical data for proper recorder integration
            await self._regenerate_historical_data(entity_id)
            return OperationResult(
                success=True, message="Statistics recalculated successfully"
            )
        except Exception as err:
            _LOGGER.exception("Error recalculating statistics for %s", entity_id)
            return OperationResult(
                success=False, message=f"Error recalculating statistics: {err}"
            )

    async def _update_statistics(self, entity_id: str) -> None:
        """Update Home Assistant statistics for an entity."""
        readings = await self.get_all_readings(entity_id)
        if not readings:
            _LOGGER.debug(
                "No readings found for %s, skipping statistics update", entity_id
            )
            return

        # Get the sensor configuration
        unit = readings[0].unit if readings else "kWh"

        # Create metadata first - external statistics need domain:id format
        statistic_id: str = (
            f"{ATTR_INTEGRATION_NAME}:{entity_id.replace('sensor.', '')}"
        )
        metadata: StatisticMetaData = {
            "mean_type": StatisticMeanType.NONE,
            "has_sum": True,
            "name": entity_id.replace("sensor.", "").replace("_", " ").title(),
            "source": ATTR_INTEGRATION_NAME,
            "statistic_id": statistic_id,
            ATTR_UNIT_OF_MEASUREMENT: unit,
        }

        # Convert readings to StatisticData
        statistics = []
        running_total = 0.0

        for reading in readings:
            # All readings are now cumulative meter readings
            running_total = reading.value

            # Round timestamp to the top of the hour for statistics
            hour_timestamp = reading.timestamp.replace(
                minute=0, second=0, microsecond=0
            )

            statistics.append(
                StatisticData(
                    start=hour_timestamp,
                    state=0.0,  # Not used for total_increasing, but required
                    sum=running_total,
                )
            )

        try:
            # Add external statistics - Home Assistant handles metadata registration
            async_add_external_statistics(self.hass, metadata, statistics)

            _LOGGER.debug(
                "Updated statistics for %s with %d data points",
                entity_id,
                len(statistics),
            )
        except ValueError as err:
            _LOGGER.warning(
                "Failed to update statistics for %s: %s",
                entity_id,
                err,
            )
        except Exception:
            _LOGGER.exception(
                "Unexpected error updating statistics for %s",
                entity_id,
            )

    async def _update_sensor_value_if_latest(
        self, entity_id: str, new_reading: Reading
    ) -> None:
        """Update sensor value only if new reading is most recent reading."""
        # All readings are now meter readings, so we can update with the latest one

        # Get all readings to check if this is the latest
        readings = await self.get_all_readings(entity_id)

        if not readings:
            return

        # Find the most recent reading by timestamp
        latest_reading = max(readings, key=lambda r: r.timestamp)

        # Only update if the new reading is the latest one
        if latest_reading.id == new_reading.id:
            # Get the sensor entity and update its value
            if (
                ATTR_INTEGRATION_NAME in self.hass.data
                and "entities" in self.hass.data[ATTR_INTEGRATION_NAME]
                and entity_id in self.hass.data[ATTR_INTEGRATION_NAME]["entities"]
            ):
                sensor = self.hass.data[ATTR_INTEGRATION_NAME]["entities"][entity_id]
                await sensor.update_value(latest_reading.value)
                _LOGGER.debug(
                    "Updated sensor %s value to %s %s (latest reading)",
                    entity_id,
                    latest_reading.value,
                    latest_reading.unit,
                )
        else:
            _LOGGER.debug(
                "Not updating sensor %s value - added reading is not the latest "
                "(timestamp: %s)",
                entity_id,
                new_reading.timestamp,
            )

    async def _update_sensor_value(self, entity_id: str) -> None:
        """Update sensor value to latest reading (used for recalculation)."""
        # Get the latest reading
        readings = await self.get_all_readings(entity_id)
        if not readings:
            return

        # Find the latest reading
        latest_reading = max(readings, key=lambda r: r.timestamp)

        # Get the sensor entity and update its value
        if (
            ATTR_INTEGRATION_NAME in self.hass.data
            and "entities" in self.hass.data[ATTR_INTEGRATION_NAME]
            and entity_id in self.hass.data[ATTR_INTEGRATION_NAME]["entities"]
        ):
            sensor = self.hass.data[ATTR_INTEGRATION_NAME]["entities"][entity_id]
            await sensor.update_value(latest_reading.value)
            _LOGGER.debug(
                "Updated sensor %s value to %s %s",
                entity_id,
                latest_reading.value,
                latest_reading.unit,
            )

    async def _inject_historical_data(self, entity_id: str, reading: Reading) -> None:
        """Inject historical data directly into Home Assistant recorder."""
        try:
            # Get entity name for display
            entity_name = entity_id.replace("sensor.", "").replace("_", " ").title()

            # Use the HistoricalDataHandler to inject the reading as historical data
            success = self._historical_handler.add_historical_statistic(
                entity_id=entity_id,
                timestamp=reading.timestamp,
                value=reading.value,
                unit=reading.unit,
                name=entity_name,
            )

            if success:
                _LOGGER.debug(
                    "Successfully injected historical data for %s: %s at %s",
                    entity_id,
                    reading.value,
                    reading.timestamp,
                )
            else:
                _LOGGER.warning(
                    "Failed to inject historical data for %s: %s at %s",
                    entity_id,
                    reading.value,
                    reading.timestamp,
                )

        except Exception:
            _LOGGER.exception("Error injecting historical data for %s", entity_id)

    async def _regenerate_historical_data(
        self, entity_id: str, *, complete_rebuild: bool = False
    ) -> None:
        """
        Regenerate all historical data for an entity after changes.

        Args:
            entity_id: The entity to regenerate data for
            complete_rebuild: If True, performs a complete wipe and rebuild

        """
        try:
            # Step 1: Handle data clearing based on rebuild type
            await self._handle_data_clearing(
                entity_id, complete_rebuild=complete_rebuild
            )

            # Step 2: Get all readings for the entity
            readings = await self.get_all_readings(entity_id)
            if not readings:
                _LOGGER.debug("No readings to regenerate for %s", entity_id)
                return

            # Step 3: Calculate consumption for readings that don't have it
            await self._calculate_missing_consumption(entity_id, readings)

            # Step 4: Generate historical data from readings
            await self._generate_historical_entries(
                entity_id, readings, complete_rebuild=complete_rebuild
            )

            # Step 5: Update current sensor value to latest cumulative reading
            await self._update_sensor_value(entity_id)

            _LOGGER.info(
                "Regenerated historical data for %s (%d readings processed, mode=%s)",
                entity_id,
                len(readings),
                "complete" if complete_rebuild else "incremental",
            )

        except Exception:
            _LOGGER.exception("Error regenerating historical data for %s", entity_id)
            raise

    async def _handle_data_clearing(
        self, entity_id: str, *, complete_rebuild: bool
    ) -> None:
        """Handle data clearing based on rebuild type."""
        if complete_rebuild:
            _LOGGER.info("Performing complete data wipe for %s", entity_id)
            clear_success = await self._historical_handler.complete_clear_entity_data(
                entity_id
            )
            if clear_success:
                _LOGGER.info("Successfully cleared all existing data for %s", entity_id)
            else:
                _LOGGER.warning("Failed to clear existing data for %s", entity_id)
        else:
            # For incremental rebuilds, just clean up invalid states
            cleanup_success = await self._historical_handler.cleanup_invalid_states(
                entity_id
            )
            if cleanup_success:
                _LOGGER.debug("Cleaned up invalid states for %s", entity_id)

    async def _calculate_missing_consumption(
        self, entity_id: str, readings: list[Reading]
    ) -> bool:
        """Calculate consumption for readings that don't have it."""
        sorted_readings = sorted(readings, key=lambda r: r.timestamp)
        readings_updated = False
        previous_reading = None

        for reading in sorted_readings:
            if reading.consumption is None and previous_reading is not None:
                # Calculate consumption from previous reading
                consumption = reading.value - previous_reading.value
                period_start = previous_reading.timestamp

                # Update the reading with consumption data
                reading.consumption = consumption
                reading.period_start = period_start
                reading.period_end = reading.timestamp
                readings_updated = True

                _LOGGER.debug(
                    "Calculated consumption for reading %s: %s %s",
                    reading.id,
                    consumption,
                    reading.unit,
                )

            previous_reading = reading

        # Save updated readings if we calculated new consumption values
        if readings_updated:
            await self.async_save()
            _LOGGER.info(
                "Updated %d readings with consumption calculations",
                len(sorted_readings),
            )

        return readings_updated

    async def _generate_historical_entries(
        self, entity_id: str, readings: list[Reading], *, complete_rebuild: bool
    ) -> None:
        """Generate historical entries from readings."""
        sorted_readings = sorted(readings, key=lambda r: r.timestamp)
        entity_name = entity_id.replace("sensor.", "").replace("_", " ").title()
        last_state_value = None
        last_state_time = None

        _LOGGER.info(
            "Generating historical entries for %d readings for %s",
            len(sorted_readings),
            entity_id,
        )

        for i, reading in enumerate(sorted_readings):
            # Add meter reading statistics
            await self._add_reading_statistics(entity_id, reading, entity_name)

            # Add consumption statistics if available
            if reading.consumption is not None and reading.consumption > 0:
                await self._add_consumption_statistics(entity_id, reading, entity_name)

            # Determine if we should add this as a state
            should_add_state = self._should_add_state(
                reading,
                complete_rebuild=complete_rebuild,
                last_state_value=last_state_value,
                last_state_time=last_state_time,
            )

            if should_add_state:
                state_success = await self._historical_handler.add_historical_state(
                    entity_id=entity_id,
                    timestamp=reading.timestamp,
                    value=reading.value,
                    unit=reading.unit,
                    force_add=True,
                )

                if state_success:
                    last_state_value = reading.value
                    last_state_time = reading.timestamp
                else:
                    _LOGGER.warning(
                        "Failed to regenerate historical state for entity %s",
                        entity_id,
                    )

            # Progress logging for large datasets
            if (i + 1) % 10 == 0 or (i + 1) == len(sorted_readings):
                _LOGGER.debug(
                    "Progress: %d/%d readings processed for %s",
                    i + 1,
                    len(sorted_readings),
                    entity_id,
                )

    async def _add_reading_statistics(
        self, entity_id: str, reading: Reading, entity_name: str
    ) -> None:
        """Add meter reading statistics."""
        success = self._historical_handler.add_historical_statistic(
            entity_id=entity_id,
            timestamp=reading.timestamp,
            value=reading.value,
            unit=reading.unit,
            name=entity_name,
        )

        if not success:
            _LOGGER.warning(
                "Failed to regenerate historical statistic for %s",
                entity_id,
            )

    async def _add_consumption_statistics(
        self, entity_id: str, reading: Reading, entity_name: str
    ) -> None:
        """Add consumption statistics."""
        if reading.consumption is None:
            return

        consumption_entity_id = f"{entity_id}_consumption"
        consumption_name = f"{entity_name} Consumption"

        consumption_success = self._historical_handler.add_historical_statistic(
            entity_id=consumption_entity_id,
            timestamp=reading.timestamp,
            value=reading.consumption,
            unit=reading.unit,
            name=consumption_name,
        )

        if not consumption_success:
            _LOGGER.warning(
                "Failed to regenerate consumption statistic for %s",
                consumption_entity_id,
            )

    def _should_add_state(
        self,
        reading: Reading,
        *,
        complete_rebuild: bool,
        last_state_value: float | None,
        last_state_time: datetime | None,
    ) -> bool:
        """Determine if a reading should be added as a state."""
        if complete_rebuild:
            # For complete rebuilds, add ALL readings as states for full history
            return True

        # For incremental rebuilds, only add significant changes
        if last_state_value is None:
            # First reading
            return True

        if abs(reading.value - last_state_value) >= MINIMUM_STATE_CHANGE:
            # Significant value change
            return True

        # At least 24 hours since last state (daily snapshots)
        return (
            last_state_time is not None
            and (reading.timestamp - last_state_time).total_seconds()
            >= DAILY_STATE_INTERVAL
        )

    # New methods for enhanced reading management

    async def add_meter_reading(
        self,
        entity_id: str,
        timestamp: datetime,
        meter_reading: float,
        notes: str = "",
        unit: str = "kWh",
    ) -> OperationResult:
        """
        Add a new meter reading and calculate consumption from previous reading.

        Args:
            entity_id: The entity ID for the meter
            timestamp: When the reading was taken
            meter_reading: The actual meter reading value
            notes: Optional notes for the reading
            unit: Unit of measurement

        Returns:
            OperationResult with success status and calculated consumption

        """
        await self.async_load()

        try:
            # Get previous reading to calculate consumption
            readings = await self.get_readings(entity_id)
            previous_reading = None
            consumption = None
            period_start = None

            if readings:
                # Find the closest previous reading
                previous_readings = [r for r in readings if r.timestamp < timestamp]
                if previous_readings:
                    previous_reading = max(previous_readings, key=lambda x: x.timestamp)
                    consumption = meter_reading - previous_reading.value
                    period_start = previous_reading.timestamp

            # Create the new reading
            reading = Reading(
                timestamp=timestamp,
                value=meter_reading,
                unit=unit,
                notes=notes,
                period_start=period_start,
                period_end=timestamp,
                consumption=consumption,
            )

            # Validate the reading
            validation = await self.validate_reading(reading)
            if not validation.is_valid:
                return OperationResult(
                    success=False,
                    message=f"Invalid reading: {', '.join(validation.errors)}",
                )

            # Add the reading
            result = await self.add_reading(entity_id, reading)

            if result.success:
                # Update any subsequent readings that may be affected
                await self._recalculate_subsequent_readings(entity_id, timestamp)

                return OperationResult(
                    success=True,
                    message=f"Added meter reading {meter_reading} {unit}"
                    + (f" (consumption: {consumption} {unit})" if consumption else ""),
                    data={
                        "meter_reading": meter_reading,
                        "consumption": consumption,
                        "period_start": period_start.isoformat()
                        if period_start
                        else None,
                        "period_end": timestamp.isoformat(),
                    },
                )

            return result

        except Exception as e:
            _LOGGER.exception("Error adding meter reading")
            error_msg = f"Failed to add meter reading: {e!s}"
            return OperationResult(success=False, message=error_msg)

    async def add_consumption_period(
        self,
        entity_id: str,
        period_start: datetime,
        period_end: datetime,
        consumption: float,
        notes: str = "",
        unit: str = "kWh",
    ) -> OperationResult:
        """
        Add consumption for a period and calculate the ending meter reading.

        Args:
            entity_id: The entity ID for the meter
            period_start: Start of the consumption period
            period_end: End of the consumption period
            consumption: Amount consumed during the period
            notes: Optional notes for the reading
            unit: Unit of measurement

        Returns:
            OperationResult with success status and calculated meter reading

        """
        await self.async_load()

        try:
            # Get readings to find the starting meter reading
            readings = await self.get_readings(entity_id)
            starting_reading = None

            if readings:
                # Find reading at or before period start
                before_readings = [r for r in readings if r.timestamp <= period_start]
                if before_readings:
                    starting_reading = max(before_readings, key=lambda x: x.timestamp)
                else:
                    # If no reading before period start, get the earliest reading
                    earliest = min(readings, key=lambda x: x.timestamp)
                    if earliest.timestamp > period_start:
                        return OperationResult(
                            success=False,
                            message=(
                                "Cannot add consumption period before "
                                "first meter reading"
                            ),
                        )

            if starting_reading is None:
                return OperationResult(
                    success=False,
                    message=(
                        "No starting meter reading found to calculate ending reading"
                    ),
                )

            # Calculate ending meter reading
            ending_meter_reading = starting_reading.value + consumption

            # Create the new reading for the end of the period
            reading = Reading(
                timestamp=period_end,
                value=ending_meter_reading,
                unit=unit,
                notes=notes,
                period_start=period_start,
                period_end=period_end,
                consumption=consumption,
            )

            # Validate the reading
            validation = await self.validate_reading(reading)
            if not validation.is_valid:
                return OperationResult(
                    success=False,
                    message=f"Invalid reading: {', '.join(validation.errors)}",
                )

            # Add the reading
            result = await self.add_reading(entity_id, reading)

            if result.success:
                # Update any subsequent readings that may be affected
                await self._recalculate_subsequent_readings(entity_id, period_end)

                return OperationResult(
                    success=True,
                    message=(
                        f"Added consumption {consumption} {unit} for period "
                        f"(ending meter reading: {ending_meter_reading} {unit})"
                    ),
                    data={
                        "consumption": consumption,
                        "meter_reading": ending_meter_reading,
                        "period_start": period_start.isoformat(),
                        "period_end": period_end.isoformat(),
                    },
                )

            return result

        except Exception as e:
            _LOGGER.exception("Error adding consumption period")
            error_msg = f"Failed to add consumption period: {e!s}"
            return OperationResult(success=False, message=error_msg)

    async def _recalculate_subsequent_readings(
        self, entity_id: str, changed_timestamp: datetime
    ) -> None:
        """
        Recalculate readings that come after a changed reading.

        This ensures that when we insert a reading in the past or modify an
        existing one, all subsequent readings are updated with correct
        consumption calculations.
        """
        try:
            readings = await self.get_readings(entity_id)

            # Get readings that come after the changed timestamp
            subsequent_readings = [
                r for r in readings if r.timestamp > changed_timestamp
            ]

            if not subsequent_readings:
                return

            # Sort by timestamp
            subsequent_readings.sort(key=lambda x: x.timestamp)

            # Find the reading at or before the changed timestamp to use as base
            base_readings = [r for r in readings if r.timestamp <= changed_timestamp]
            if not base_readings:
                return

            base_reading = max(base_readings, key=lambda x: x.timestamp)

            # Recalculate each subsequent reading
            previous_reading = base_reading
            for reading in subsequent_readings:
                if previous_reading:
                    # Update consumption calculation
                    reading.consumption = reading.value - previous_reading.value
                    reading.period_start = previous_reading.timestamp
                    reading.period_end = reading.timestamp

                    # Update the reading in storage
                    await self._update_reading_in_storage(entity_id, reading)

                previous_reading = reading

        except Exception:
            _LOGGER.exception("Error recalculating subsequent readings")

    async def _update_reading_in_storage(
        self, entity_id: str, reading: Reading
    ) -> None:
        """Update a specific reading in storage."""
        if entity_id not in self._data:
            return

        # Find and update the reading
        for i, stored_reading in enumerate(self._data[entity_id]):
            if stored_reading.id == reading.id:
                self._data[entity_id][i] = reading
                break

        # Save to storage
        await self.async_save()

    async def rebuild_history(
        self, entity_id: str, *, complete_wipe: bool = True
    ) -> OperationResult:
        """
        Completely rebuild historical data for an entity.

        This method will:
        1. Optionally clear all existing historical data
        2. Calculate consumption for readings that don't have it
        3. Regenerate historical statistics and states
        4. Update current sensor values

        Args:
            entity_id: The entity to rebuild
            complete_wipe: If True, performs complete data wipe before rebuild

        """
        try:
            _LOGGER.info(
                "Starting %s history rebuild for %s",
                "complete" if complete_wipe else "incremental",
                entity_id,
            )

            # Step 1: Validate database access
            if not await self._historical_handler.validate_database_access():
                return OperationResult(
                    success=False,
                    message="Cannot access Home Assistant database",
                )

            # Step 2: Perform complete rebuild with optional wipe
            await self._regenerate_historical_data(
                entity_id, complete_rebuild=complete_wipe
            )

            # Step 3: Update statistics for long-term trends
            await self._update_statistics(entity_id)

            # Step 4: Get readings count for confirmation
            readings = await self.get_all_readings(entity_id)
            readings_count = len(readings)

            _LOGGER.info(
                "Successfully rebuilt history for %s (%d readings processed, mode=%s)",
                entity_id,
                readings_count,
                "complete" if complete_wipe else "incremental",
            )

            return OperationResult(
                success=True,
                message=(
                    f"History rebuilt successfully "
                    f"({readings_count} readings processed, "
                    f"mode={'complete' if complete_wipe else 'incremental'}, "
                    f"consumption calculations updated)"
                ),
            )

        except Exception as err:
            _LOGGER.exception("Error rebuilding history for %s", entity_id)
            return OperationResult(
                success=False, message=f"Failed to rebuild history: {err}"
            )
