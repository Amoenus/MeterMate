"""Data management interface for MeterMate."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.helpers import storage
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .models import OperationResult, Reading, ReadingType, ValidationResult

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_readings"


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

        # Update the sensor value to the latest cumulative reading
        await self._update_sensor_value(entity_id)

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

                # Update the sensor value to the latest cumulative reading
                await self._update_sensor_value(entity_id)

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

                # Update the sensor value to the latest cumulative reading
                await self._update_sensor_value(entity_id)

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

        # Update the sensor value to the latest cumulative reading
        await self._update_sensor_value(entity_id)

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

        # Check value is non-negative for cumulative readings
        if reading.reading_type == ReadingType.CUMULATIVE and reading.value < 0:
            errors.append("Cumulative readings must be non-negative")

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
            # Also update the sensor value to the latest cumulative reading
            await self._update_sensor_value(entity_id)
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

        # Create metadata first - use proper statistic_id format for external statistics
        statistic_id = f"{DOMAIN}:{entity_id}"
        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name=entity_id.replace("sensor.", "").replace("_", " ").title(),
            source=DOMAIN,
            statistic_id=statistic_id,
            unit_of_measurement=unit,
        )

        # Convert readings to StatisticData
        statistics = []
        running_total = 0.0

        for reading in readings:
            if reading.reading_type == ReadingType.CUMULATIVE:
                running_total = reading.value
            else:  # PERIODIC
                running_total += reading.value

            statistics.append(
                StatisticData(
                    start=reading.timestamp,
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

    async def _update_sensor_value(self, entity_id: str) -> None:
        """Update the sensor value to the latest cumulative reading."""
        # Get the latest cumulative reading
        readings = await self.get_all_readings(entity_id)
        if not readings:
            return

        # Find the latest cumulative reading
        cumulative_readings = [
            r for r in readings if r.reading_type == ReadingType.CUMULATIVE
        ]
        if not cumulative_readings:
            return

        latest_reading = max(cumulative_readings, key=lambda r: r.timestamp)

        # Get the sensor entity and update its value
        if (
            DOMAIN in self.hass.data
            and "entities" in self.hass.data[DOMAIN]
            and entity_id in self.hass.data[DOMAIN]["entities"]
        ):
            sensor = self.hass.data[DOMAIN]["entities"][entity_id]
            await sensor.update_value(latest_reading.value)
            _LOGGER.debug(
                "Updated sensor %s value to %s %s",
                entity_id,
                latest_reading.value,
                latest_reading.unit,
            )
