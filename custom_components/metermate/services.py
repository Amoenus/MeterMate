"""Services for MeterMate integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.util import dt as dt_util

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
    LOGGER.info("Updating statistic for %s: %s at %s", entity_id, new_total, timestamp)

    # Try to find the entity object to update it properly
    found_entity = False

    # Debug: Log what we're looking for
    LOGGER.debug("Looking for entity %s in entity platforms", entity_id)

    # Search through all loaded entities to find our MeterMate sensor
    for platform_key, domain_data in hass.data.get("entity_platform", {}).items():
        LOGGER.debug("Checking platform: %s", platform_key)
        if hasattr(domain_data, "entities"):
            LOGGER.debug(
                "Platform %s has %d entities", platform_key, len(domain_data.entities)
            )
            for entity in domain_data.entities:
                if hasattr(entity, "entity_id"):
                    LOGGER.debug("Found entity: %s", entity.entity_id)
                    if entity.entity_id == entity_id and hasattr(
                        entity, "update_value"
                    ):
                        await entity.update_value(new_total)
                        found_entity = True
                        LOGGER.debug(
                            "Updated entity %s via update_value to %s",
                            entity_id,
                            new_total,
                        )
                        break

    if not found_entity:
        LOGGER.debug("Entity not found via platform search, using fallback")
        # Fallback: update state directly but preserve all attributes
        current_state = hass.states.get(entity_id)
        if current_state:
            # Preserve existing attributes and add our updates
            new_attributes = dict(current_state.attributes)
            new_attributes.update(
                {
                    "last_updated": timestamp.isoformat(),
                    "last_reading": new_total,
                }
            )

            hass.states.async_set(entity_id, str(new_total), attributes=new_attributes)
            LOGGER.debug(
                "Updated entity %s state via state machine to %s", entity_id, new_total
            )
        else:
            LOGGER.error("Entity %s not found", entity_id)


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services for MeterMate."""
    hass.services.async_remove(DOMAIN, SERVICE_ADD_READING)
