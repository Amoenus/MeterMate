"""Services for MeterMate integration using the new data management interface."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .data_manager import MeterMateDataManager, TimePeriod
from .models import Reading

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

_LOGGER = logging.getLogger(__name__)

# Service names
SERVICE_ADD_READING = "add_reading"
SERVICE_UPDATE_READING = "update_reading"
SERVICE_DELETE_READING = "delete_reading"
SERVICE_GET_READINGS = "get_readings"
SERVICE_BULK_IMPORT = "bulk_import"
SERVICE_RECALCULATE_STATISTICS = "recalculate_statistics"
SERVICE_REBUILD_HISTORY = "rebuild_history"

# New enhanced services for meter readings and consumption
SERVICE_ADD_METER_READING = "add_meter_reading"
SERVICE_ADD_CONSUMPTION_PERIOD = "add_consumption_period"

# Service schemas
SERVICE_ADD_READING_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("value"): vol.Coerce(float),
        vol.Optional("timestamp"): cv.datetime,
        vol.Optional("unit", default="kWh"): cv.string,
        vol.Optional("notes"): cv.string,
    }
)

SERVICE_UPDATE_READING_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("reading_id"): cv.string,
        vol.Required("value"): vol.Coerce(float),
        vol.Optional("timestamp"): cv.datetime,
        vol.Optional("unit", default="kWh"): cv.string,
        vol.Optional("notes"): cv.string,
    }
)

SERVICE_DELETE_READING_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("reading_id"): cv.string,
    }
)

SERVICE_GET_READINGS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("start_date"): cv.datetime,
        vol.Optional("end_date"): cv.datetime,
    }
)

SERVICE_BULK_IMPORT_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("readings"): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required("timestamp"): cv.datetime,
                        vol.Required("value"): vol.Coerce(float),
                        vol.Optional("unit", default="kWh"): cv.string,
                        vol.Optional("notes"): cv.string,
                    }
                )
            ],
        ),
    }
)

SERVICE_RECALCULATE_STATISTICS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
    }
)

SERVICE_REBUILD_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("complete_wipe", default=True): cv.boolean,
    }
)

# New service schemas
SERVICE_ADD_METER_READING_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("meter_reading"): vol.Coerce(float),
        vol.Optional("timestamp"): cv.datetime,
        vol.Optional("unit", default="kWh"): cv.string,
        vol.Optional("notes", default=""): cv.string,
    }
)

SERVICE_ADD_CONSUMPTION_PERIOD_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("consumption"): vol.Coerce(float),
        vol.Required("period_start"): cv.datetime,
        vol.Required("period_end"): cv.datetime,
        vol.Optional("unit", default="kWh"): cv.string,
        vol.Optional("notes", default=""): cv.string,
    }
)


class MeterMateServices:
    """Service handler for MeterMate integration."""

    def __init__(self, hass: HomeAssistant, data_manager: MeterMateDataManager) -> None:
        """Initialize the service handler."""
        self.hass = hass
        self.data_manager = data_manager

    async def async_register_services(self) -> None:
        """Register all MeterMate services."""
        _LOGGER.info("Registering MeterMate services")

        # Register add_reading service
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_ADD_READING,
            self._handle_add_reading,
            schema=SERVICE_ADD_READING_SCHEMA,
        )

        # Register update_reading service
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_READING,
            self._handle_update_reading,
            schema=SERVICE_UPDATE_READING_SCHEMA,
        )

        # Register delete_reading service
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_DELETE_READING,
            self._handle_delete_reading,
            schema=SERVICE_DELETE_READING_SCHEMA,
        )

        # Register get_readings service
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_GET_READINGS,
            self._handle_get_readings,
            schema=SERVICE_GET_READINGS_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )

        # Register bulk_import service
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_BULK_IMPORT,
            self._handle_bulk_import,
            schema=SERVICE_BULK_IMPORT_SCHEMA,
        )

        # Register recalculate_statistics service
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_RECALCULATE_STATISTICS,
            self._handle_recalculate_statistics,
            schema=SERVICE_RECALCULATE_STATISTICS_SCHEMA,
        )

        # Register rebuild_history service
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_REBUILD_HISTORY,
            self._handle_rebuild_history,
            schema=SERVICE_REBUILD_HISTORY_SCHEMA,
        )

        # Register new enhanced services
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_ADD_METER_READING,
            self._handle_add_meter_reading,
            schema=SERVICE_ADD_METER_READING_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_ADD_CONSUMPTION_PERIOD,
            self._handle_add_consumption_period,
            schema=SERVICE_ADD_CONSUMPTION_PERIOD_SCHEMA,
        )

        _LOGGER.info("MeterMate services registered successfully")

    async def async_unregister_services(self) -> None:
        """Unregister all MeterMate services."""
        services_to_remove = [
            SERVICE_ADD_READING,
            SERVICE_UPDATE_READING,
            SERVICE_DELETE_READING,
            SERVICE_GET_READINGS,
            SERVICE_BULK_IMPORT,
            SERVICE_RECALCULATE_STATISTICS,
            SERVICE_REBUILD_HISTORY,
            SERVICE_ADD_METER_READING,
            SERVICE_ADD_CONSUMPTION_PERIOD,
        ]

        for service in services_to_remove:
            self.hass.services.async_remove(DOMAIN, service)

        _LOGGER.info("MeterMate services unregistered")

    async def _handle_add_reading(self, call: ServiceCall) -> None:
        """Handle add_reading service call."""
        entity_id = call.data["entity_id"]
        value = call.data["value"]
        timestamp = call.data.get("timestamp", dt_util.utcnow())
        unit = call.data.get("unit", "kWh")
        notes = call.data.get("notes")

        # Ensure timestamp is timezone-aware
        if timestamp is not None:
            timestamp = dt_util.as_utc(timestamp)

        # Create reading object - all readings are now meter readings
        reading = Reading(
            timestamp=timestamp,
            value=value,
            unit=unit,
            notes=notes,
        )

        # Add the reading
        result = await self.data_manager.add_reading(entity_id, reading)

        if result.success:
            _LOGGER.info(
                "Successfully added reading for %s: %s %s at %s",
                entity_id,
                value,
                unit,
                timestamp,
            )
        else:
            _LOGGER.error(
                "Failed to add reading for %s: %s",
                entity_id,
                result.message,
            )

    async def _handle_update_reading(self, call: ServiceCall) -> None:
        """Handle update_reading service call."""
        entity_id = call.data["entity_id"]
        reading_id = call.data["reading_id"]
        value = call.data["value"]
        timestamp = call.data.get("timestamp", dt_util.utcnow())
        unit = call.data.get("unit", "kWh")
        notes = call.data.get("notes")

        # Ensure timestamp is timezone-aware
        if timestamp is not None:
            timestamp = dt_util.as_utc(timestamp)

        # Create updated reading object - all readings are now meter readings
        updated_reading = Reading(
            timestamp=timestamp,
            value=value,
            unit=unit,
            notes=notes,
        )

        # Update the reading
        result = await self.data_manager.update_reading(
            entity_id, reading_id, updated_reading
        )

        if result.success:
            _LOGGER.info(
                "Successfully updated reading %s for %s",
                reading_id,
                entity_id,
            )
        else:
            _LOGGER.error(
                "Failed to update reading %s for %s: %s",
                reading_id,
                entity_id,
                result.message,
            )

    async def _handle_delete_reading(self, call: ServiceCall) -> None:
        """Handle delete_reading service call."""
        entity_id = call.data["entity_id"]
        reading_id = call.data["reading_id"]

        # Delete the reading
        result = await self.data_manager.delete_reading(entity_id, reading_id)

        if result.success:
            _LOGGER.info(
                "Successfully deleted reading %s for %s",
                reading_id,
                entity_id,
            )
        else:
            _LOGGER.error(
                "Failed to delete reading %s for %s: %s",
                reading_id,
                entity_id,
                result.message,
            )

    async def _handle_get_readings(self, call: ServiceCall) -> dict:
        """Handle get_readings service call."""
        # Debug: Log the entire call object to understand its structure
        _LOGGER.info("GET_READINGS service call object: %s", call)
        _LOGGER.info("Call data: %s", call.data)

        # Try to get entity_id from data
        entity_id = call.data.get("entity_id")

        if not entity_id:
            error_msg = "entity_id is required"
            raise HomeAssistantError(error_msg)

        start_date = call.data.get("start_date")
        end_date = call.data.get("end_date")

        _LOGGER.info("GET_READINGS service called for entity: %s", entity_id)
        _LOGGER.info("Service call data: %s", call.data)

        # Ensure dates are timezone-aware
        if start_date is not None:
            start_date = dt_util.as_utc(start_date)
        if end_date is not None:
            end_date = dt_util.as_utc(end_date)

        period = None
        if start_date and end_date:
            period = TimePeriod(start=start_date, end=end_date)

        # Get the readings
        readings = await self.data_manager.get_readings(entity_id, period)

        _LOGGER.info(
            "Retrieved %d readings for %s",
            len(readings),
            entity_id,
        )

        # Log the readings for debugging and return response
        readings_data = []
        for reading in readings:
            reading_dict = {
                "id": reading.id,
                "timestamp": reading.timestamp.isoformat(),
                "value": reading.value,
                "unit": reading.unit,
                "notes": reading.notes,
                "period_start": (
                    reading.period_start.isoformat() if reading.period_start else None
                ),
                "period_end": (
                    reading.period_end.isoformat() if reading.period_end else None
                ),
                "consumption": reading.consumption,
            }
            readings_data.append(reading_dict)
            _LOGGER.info(
                "Reading: id=%s, timestamp=%s, value=%s, unit=%s, consumption=%s",
                reading.id,
                reading.timestamp.isoformat(),
                reading.value,
                reading.unit,
                reading.consumption,
            )

        response = {"readings": readings_data}
        _LOGGER.info("Returning response with %d readings", len(readings_data))
        return response

    async def _handle_bulk_import(self, call: ServiceCall) -> None:
        """Handle bulk_import service call."""
        entity_id = call.data["entity_id"]
        readings_data = call.data["readings"]

        # Convert readings data to Reading objects
        readings = []
        for reading_data in readings_data:
            # Ensure timestamp is timezone-aware
            timestamp = reading_data["timestamp"]
            if timestamp is not None:
                timestamp = dt_util.as_utc(timestamp)

            # All readings are now meter readings
            reading = Reading(
                timestamp=timestamp,
                value=reading_data["value"],
                unit=reading_data.get("unit", "kWh"),
                notes=reading_data.get("notes"),
            )
            readings.append(reading)

        # Bulk import the readings
        result = await self.data_manager.bulk_import(entity_id, readings)

        _LOGGER.info(
            "Bulk import for %s completed: %d successful, %d errors",
            entity_id,
            result["success_count"],
            result["error_count"],
        )

        if result["errors"]:
            _LOGGER.warning("Bulk import errors: %s", result["errors"])

    async def _handle_recalculate_statistics(self, call: ServiceCall) -> None:
        """Handle recalculate_statistics service call."""
        entity_id = call.data["entity_id"]

        # Recalculate statistics
        result = await self.data_manager.recalculate_statistics(entity_id)

        if result.success:
            _LOGGER.info(
                "Successfully recalculated statistics for %s",
                entity_id,
            )
        else:
            _LOGGER.error(
                "Failed to recalculate statistics for %s: %s",
                entity_id,
                result.message,
            )

    async def _handle_rebuild_history(self, call: ServiceCall) -> None:
        """Handle rebuild_history service call."""
        entity_id = call.data["entity_id"]
        complete_wipe = call.data.get("complete_wipe", True)

        _LOGGER.info(
            "Starting %s rebuild for %s",
            "complete" if complete_wipe else "incremental",
            entity_id,
        )

        # Rebuild history with specified mode
        result = await self.data_manager.rebuild_history(
            entity_id, complete_wipe=complete_wipe
        )

        if result.success:
            _LOGGER.info(
                "Successfully rebuilt history for %s: %s",
                entity_id,
                result.message,
            )
        else:
            _LOGGER.error(
                "Failed to rebuild history for %s: %s",
                entity_id,
                result.message,
            )

    async def _handle_add_meter_reading(self, call: ServiceCall) -> None:
        """Add a meter reading and calculate consumption."""
        entity_id = call.data["entity_id"]
        meter_reading = call.data["meter_reading"]
        timestamp = call.data.get("timestamp", dt_util.utcnow())
        notes = call.data.get("notes", "")
        unit = call.data.get("unit", "kWh")

        try:
            result = await self.data_manager.add_meter_reading(
                entity_id=entity_id,
                timestamp=timestamp,
                meter_reading=meter_reading,
                notes=notes,
                unit=unit,
            )

            if not result.success:
                raise HomeAssistantError(result.message)

            _LOGGER.info(
                "Added meter reading for %s: %s %s",
                entity_id,
                meter_reading,
                unit,
            )

        except Exception as e:
            _LOGGER.exception("Error adding meter reading")
            error_msg = f"Failed to add meter reading: {e!s}"
            raise HomeAssistantError(error_msg) from e

    async def _handle_add_consumption_period(self, call: ServiceCall) -> None:
        """Add consumption for a period and calculate ending meter reading."""
        entity_id = call.data["entity_id"]
        consumption = call.data["consumption"]
        period_start = call.data["period_start"]
        period_end = call.data["period_end"]
        notes = call.data.get("notes", "")
        unit = call.data.get("unit", "kWh")

        try:
            result = await self.data_manager.add_consumption_period(
                entity_id=entity_id,
                period_start=period_start,
                period_end=period_end,
                consumption=consumption,
                notes=notes,
                unit=unit,
            )

            if not result.success:
                raise HomeAssistantError(result.message)

            _LOGGER.info(
                "Added consumption period for %s: %s %s from %s to %s",
                entity_id,
                consumption,
                unit,
                period_start,
                period_end,
            )

        except Exception as e:
            _LOGGER.exception("Error adding consumption period")
            error_msg = f"Failed to add consumption period: {e!s}"
            raise HomeAssistantError(error_msg) from e


async def async_setup_services(
    hass: HomeAssistant, data_manager: MeterMateDataManager
) -> None:
    """Set up MeterMate services."""
    services = MeterMateServices(hass, data_manager)
    await services.async_register_services()

    # Store the services instance for later cleanup
    hass.data.setdefault(DOMAIN, {})["services"] = services


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload MeterMate services."""
    if DOMAIN in hass.data and "services" in hass.data[DOMAIN]:
        services = hass.data[DOMAIN]["services"]
        await services.async_unregister_services()
        del hass.data[DOMAIN]["services"]
