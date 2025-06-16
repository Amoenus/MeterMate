"""Services for MeterMate integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.util import dt as dt_util

# For historical data, we'll use a different approach
HAS_RECORDER = False
HAS_STATISTICS = False

try:
    from homeassistant.components.recorder.statistics import (
        StatisticData,
        StatisticMetaData,
        async_add_external_statistics,
    )
    HAS_STATISTICS = True
except ImportError:
    pass

from .const import (
    ATTR_END_DATE,
    ATTR_ENTITY_ID,
    ATTR_MODE,
    ATTR_START_DATE,
    ATTR_TIMESTAMP,
    ATTR_VALUE,
    DOMAIN,
    LOGGER,
    MODE_CUMULATIVE,
    MODE_PERIODIC,
    SERVICE_ADD_READING,
)

if TYPE_CHECKING:
    from datetime import datetime
    from homeassistant.core import HomeAssistant, ServiceCall

SERVICE_ADD_READING_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_VALUE): vol.Coerce(float),
        vol.Optional(ATTR_MODE, default=MODE_CUMULATIVE): vol.In(
            [MODE_CUMULATIVE, MODE_PERIODIC]
        ),
        vol.Optional(ATTR_TIMESTAMP): cv.datetime,
        vol.Optional(ATTR_START_DATE): cv.date,
        vol.Optional(ATTR_END_DATE): cv.date,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for MeterMate."""

    async def handle_add_reading(call: ServiceCall) -> None:
        """Handle the add_reading service call."""
        entity_id = call.data[ATTR_ENTITY_ID]
        value = call.data[ATTR_VALUE]
        mode = call.data[ATTR_MODE]

        # Validate entity
        if not await _validate_entity(hass, entity_id):
            return

        # Validate mode-specific required fields
        if mode == MODE_PERIODIC:
            start_date = call.data.get(ATTR_START_DATE)
            end_date = call.data.get(ATTR_END_DATE)
            if not start_date or not end_date:
                LOGGER.error(
                    "start_date and end_date are required for periodic mode"
                )
                return
        elif mode == MODE_CUMULATIVE:
            timestamp = call.data.get(ATTR_TIMESTAMP)
            if not timestamp:
                LOGGER.warning(
                    "No timestamp provided for cumulative reading. "
                    "Data will be recorded for current time. "
                    "For historical data, provide a timestamp."
                )

        # Get current state
        current_total = await _get_current_total(hass, entity_id)
        if current_total is None:
            return

        # Get initial reading
        initial_reading = await _get_initial_reading(hass, entity_id)

        # Process reading based on mode
        if mode == MODE_CUMULATIVE:
            await _process_cumulative_reading(
                hass, call, entity_id, value, initial_reading
            )
        elif mode == MODE_PERIODIC:
            await _process_periodic_reading(hass, call, entity_id, value, current_total)

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_READING,
        handle_add_reading,
        schema=SERVICE_ADD_READING_SCHEMA,
    )


async def _validate_entity(hass: HomeAssistant, entity_id: str) -> bool:
    """Validate that the entity exists and is a MeterMate entity."""
    entity_registry = async_get_entity_registry(hass)
    entity_entry = entity_registry.async_get(entity_id)

    if not entity_entry:
        LOGGER.error("Entity %s not found", entity_id)
        return False

    if entity_entry.platform != DOMAIN:
        LOGGER.error("Entity %s is not a MeterMate entity", entity_id)
        return False

    return True


async def _get_current_total(hass: HomeAssistant, entity_id: str) -> float | None:
    """Get the current total from the entity state."""
    state = hass.states.get(entity_id)
    if not state:
        LOGGER.error("State for entity %s not found", entity_id)
        return None

    try:
        if state.state not in ("unknown", "unavailable"):
            return float(state.state)
        return 0.0
    except (ValueError, TypeError):
        return 0.0


async def _get_initial_reading(hass: HomeAssistant, entity_id: str) -> float:
    """Get the initial reading from the config entry."""
    entity_registry = async_get_entity_registry(hass)
    entity_entry = entity_registry.async_get(entity_id)

    if not entity_entry:
        return 0.0

    config_entries = hass.config_entries.async_entries(DOMAIN)
    for entry in config_entries:
        if entry.entry_id == entity_entry.config_entry_id:
            return float(entry.data.get("initial_reading", 0))

    return 0.0


async def _process_cumulative_reading(
    hass: HomeAssistant,
    call: ServiceCall,
    entity_id: str,
    value: float,
    initial_reading: float,
) -> None:
    """Process a cumulative reading."""
    timestamp = call.data.get(ATTR_TIMESTAMP)
    if timestamp is None:
        # If no timestamp provided, log a warning and use current time
        LOGGER.warning(
            "No timestamp provided for cumulative reading. Using current time. "
            "Consider providing a timestamp for accurate historical data."
        )
        timestamp = dt_util.now()
    elif timestamp.tzinfo is None:
        timestamp = dt_util.as_local(timestamp)

    # Calculate new total: reading - initial_reading
    new_total = value - initial_reading

    # Import the statistic
    await _import_statistic(hass, entity_id, timestamp, new_total)

    state = hass.states.get(entity_id)
    unit = state.attributes.get("unit_of_measurement", "") if state else ""

    LOGGER.info(
        "Added cumulative reading for %s: %s %s (new total: %s)",
        entity_id,
        value,
        unit,
        new_total,
    )


async def _process_periodic_reading(
    hass: HomeAssistant,
    call: ServiceCall,
    entity_id: str,
    value: float,
    current_total: float,
) -> None:
    """Process a periodic reading."""
    start_date = call.data.get(ATTR_START_DATE)
    end_date = call.data.get(ATTR_END_DATE)

    if not start_date or not end_date:
        LOGGER.error("start_date and end_date are required for periodic mode")
        return

    # Use end_date as the timestamp
    timestamp = dt_util.start_of_local_day(end_date)
    timestamp = timestamp.replace(hour=23, minute=59, second=59)

    # Add consumption to current total
    new_total = current_total + value

    # Import the statistic
    await _import_statistic(hass, entity_id, timestamp, new_total)

    state = hass.states.get(entity_id)
    unit = state.attributes.get("unit_of_measurement", "") if state else ""

    LOGGER.info(
        "Added periodic reading for %s: %s %s (period: %s to %s, new total: %s)",
        entity_id,
        value,
        unit,
        start_date,
        end_date,
        new_total,
    )


async def _import_statistic(
    hass: HomeAssistant, entity_id: str, timestamp: datetime, new_total: float
) -> None:
    """Import a statistic into Home Assistant."""
    LOGGER.info(
        "Processing statistic for %s: %s at %s", entity_id, new_total, timestamp
    )

    # Try to import historical statistic if not today
    current_date = dt_util.now().date()
    statistic_date = timestamp.date()
    
    if statistic_date != current_date:
        # This is historical data, try to import as historical statistic
        await _add_historical_statistic(hass, entity_id, timestamp, new_total)
    else:
        # This is current data, update current state
        await _update_current_state(hass, entity_id, new_total)

    LOGGER.info(
        "Processed statistic for %s: %s", entity_id, new_total
    )


async def _add_historical_statistic(
    hass: HomeAssistant, entity_id: str, timestamp: datetime, value: float
) -> None:
    """Add historical statistic to Home Assistant statistics database."""
    if not HAS_STATISTICS:
        LOGGER.warning(
            "Statistics components not available. Cannot import historical data for %s",
            entity_id,
        )
        # Fallback to updating current state
        await _update_current_state(hass, entity_id, value)
        return
    
    try:
        # Get entity state for unit and device class
        state = hass.states.get(entity_id)
        if not state:
            LOGGER.error("Entity %s not found for historical import", entity_id)
            return
        
        unit = state.attributes.get("unit_of_measurement", "")
        
        # Create statistic metadata
        metadata = StatisticMetaData(
            source=DOMAIN,
            statistic_id=f"{DOMAIN}:{entity_id.replace('sensor.', '')}",
            unit_of_measurement=unit,
            has_mean=False,
            has_sum=True,
            name=state.attributes.get("friendly_name", entity_id),
        )
        
        # Create statistic data
        statistic_data = StatisticData(
            start=timestamp,
            sum=value,
            state=value,
        )
        
        # Import the statistics
        async_add_external_statistics(
            hass,
            metadata,
            [statistic_data],
        )
        
        LOGGER.info(
            "Successfully imported historical statistic for %s: %s at %s",
            entity_id,
            value,
            timestamp,
        )
        
        # Also update current state if this is the most recent data
        current_state_value = 0.0
        try:
            if state.state not in ("unknown", "unavailable"):
                current_state_value = float(state.state)
        except (ValueError, TypeError):
            pass
            
        if value > current_state_value:
            await _update_current_state(hass, entity_id, value)
            
    except (ValueError, TypeError, AttributeError, ImportError) as e:
        LOGGER.error(
            "Error importing historical statistic for %s: %s",
            entity_id,
            e,
        )
        # Fallback to updating current state
        await _update_current_state(hass, entity_id, value)


# Temporarily disabled to prevent Home Assistant loading issues
# async def _add_historical_statistic(
#     hass: HomeAssistant, entity_id: str, timestamp: datetime, value: float
# ) -> None:
#     """Add historical statistic to Home Assistant statistics database."""
#     # This function is temporarily disabled
#     pass


async def _update_current_state(
    hass: HomeAssistant, entity_id: str, value: float
) -> None:
    """Update the current state of the entity."""
    if DOMAIN in hass.data and "entities" in hass.data[DOMAIN]:
        entity = hass.data[DOMAIN]["entities"].get(entity_id)
        if entity and hasattr(entity, "update_value"):
            LOGGER.debug("Updating current state for %s to %s", entity_id, value)
            await entity.update_value(value)
            LOGGER.debug("Successfully updated current state for %s", entity_id)
        else:
            LOGGER.error(
                "Could not find entity object for %s to update state", entity_id
            )
    else:
        LOGGER.error("Domain data not found for %s", entity_id)


# Historical data handling function removed to prevent loading issues
# This complex function was causing Home Assistant to hang during startup


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services for MeterMate."""
    hass.services.async_remove(DOMAIN, SERVICE_ADD_READING)
