#!/usr/bin/env python3
"""Sensor platform for MeterMate."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_NAME, CONF_UNIT_OF_MEASUREMENT
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_DEVICE_CLASS, CONF_INITIAL_READING, DOMAIN

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import MeterMateConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: MeterMateConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities([MeterMateSensor(entry)])


class MeterMateSensor(SensorEntity, RestoreEntity):
    """MeterMate sensor class."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, entry: MeterMateConfigEntry) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._attr_name = entry.data[CONF_NAME]
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}"

        # Handle unit of measurement - provide default if None
        unit = entry.data.get(CONF_UNIT_OF_MEASUREMENT)
        device_class = entry.data.get(CONF_DEVICE_CLASS)

        # Debug logging to track configuration values
        _LOGGER.debug("Sensor init - entry.data: %s", entry.data)
        _LOGGER.debug("Sensor init - unit from config: %s", unit)
        _LOGGER.debug("Sensor init - device_class from config: %s", device_class)

        # Set default unit based on device class if not provided
        if not unit:
            if device_class == "energy":
                unit = "kWh"
            elif device_class == "gas":
                unit = "m³"
            elif device_class == "water":
                unit = "L"
            else:
                unit = "kWh"  # Default fallback

        _LOGGER.debug("Sensor init - final unit: %s", unit)

        # Ensure unit is not None
        if unit is None:
            unit = "kWh"

        self._attr_native_unit_of_measurement = unit
        if device_class:
            self._attr_device_class = SensorDeviceClass(device_class)
        else:
            self._attr_device_class = None
        self._initial_reading = entry.data.get(CONF_INITIAL_READING, 0)
        # Don't initialize to 0.0 - let state restoration handle it
        self._attr_native_value = None
        # Track the last known good value to prevent unwanted resets
        self._last_good_value = None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information about this sensor."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._attr_name,
            "manufacturer": "MeterMate",
            "model": "Manual Meter",
            "sw_version": "1.0.0",
        }

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Register this entity in our domain data for service access
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}
        if "entities" not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN]["entities"] = {}

        self.hass.data[DOMAIN]["entities"][self.entity_id] = self
        _LOGGER.debug("Registered entity %s in domain data", self.entity_id)

        # Restore the last state if available
        if (last_state := await self.async_get_last_state()) is not None:
            _LOGGER.debug("Restoring state: %s", last_state.state)
            try:
                # Skip invalid states
                if last_state.state not in [None, "", "unavailable", "unknown"]:
                    restored_value = float(last_state.state)

                    # Check for stored last good value in attributes
                    last_good_from_attrs = None
                    if hasattr(last_state, "attributes") and last_state.attributes:
                        last_good_from_attrs = last_state.attributes.get(
                            "last_good_value"
                        )

                    # If we have a last good value and restored value is 0,
                    # this might be an unwanted reset
                    if (
                        last_good_from_attrs is not None
                        and restored_value == 0.0
                        and float(last_good_from_attrs) > 0
                    ):
                        _LOGGER.warning(
                            "Detected potential unwanted reset to 0. "
                            "Last good value: %s, restored: %s. "
                            "Using last good value.",
                            last_good_from_attrs,
                            restored_value,
                        )
                        self._attr_native_value = float(last_good_from_attrs)
                        self._last_good_value = float(last_good_from_attrs)
                    else:
                        self._attr_native_value = restored_value
                        # Track last good value (anything > 0)
                        if restored_value > 0:
                            self._last_good_value = restored_value
                        _LOGGER.debug(
                            "Successfully restored state to: %s", restored_value
                        )
                else:
                    _LOGGER.debug(
                        "Invalid state '%s', using initial reading: %s",
                        last_state.state,
                        self._initial_reading,
                    )
                    self._attr_native_value = float(self._initial_reading)
            except (ValueError, TypeError) as e:
                _LOGGER.debug(
                    "Error restoring state '%s': %s, using initial reading: %s",
                    last_state.state,
                    e,
                    self._initial_reading,
                )
                self._attr_native_value = float(self._initial_reading)
        else:
            # If no previous state, use initial reading
            _LOGGER.debug(
                "No previous state, using initial reading: %s", self._initial_reading
            )
            self._attr_native_value = float(self._initial_reading)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attributes = {
            "initial_reading": self._initial_reading,
            "integration": DOMAIN,
        }

        # Store last good value to help with recovery from unwanted resets
        if self._last_good_value is not None:
            attributes["last_good_value"] = self._last_good_value

        return attributes

    async def update_value(self, new_value: float) -> None:
        """Update the sensor value."""
        old_value = self._attr_native_value

        _LOGGER.info("update_value called: old=%s, new=%s", old_value, new_value)

        # Protect against unwanted resets to 0.0
        if (
            new_value == 0.0
            and old_value is not None
            and isinstance(old_value, (int, float))
            and old_value > 0
        ):
            _LOGGER.warning(
                "Attempted to reset sensor %s from %s to 0.0. "
                "This may be an unwanted reset. Rejecting update.",
                self.entity_id,
                old_value,
            )
            # Don't update the value, keep the current one
            return

        self._attr_native_value = new_value

        # Track last good value (any value > 0) for recovery purposes
        if new_value > 0:
            self._last_good_value = new_value

        _LOGGER.info("Updating sensor value from %s to %s", old_value, new_value)
        _LOGGER.debug("Last good value updated to: %s", self._last_good_value)

        self.async_write_ha_state()
        _LOGGER.info("State written to Home Assistant")

    def async_write_ha_state(self) -> None:
        """Write the state to Home Assistant."""
        _LOGGER.info(
            "async_write_ha_state called: current value=%s", self._attr_native_value
        )
        super().async_write_ha_state()
        _LOGGER.info("async_write_ha_state completed")

    async def async_will_remove_from_hass(self) -> None:
        """When entity is being removed from hass."""
        # Clean up our entity registry
        if (
            DOMAIN in self.hass.data
            and "entities" in self.hass.data[DOMAIN]
            and self.entity_id in self.hass.data[DOMAIN]["entities"]
        ):
            del self.hass.data[DOMAIN]["entities"][self.entity_id]
            _LOGGER.debug("Unregistered entity %s from domain data", self.entity_id)

        await super().async_will_remove_from_hass()

    async def async_update(self) -> None:
        """Update the sensor by fetching the latest data from storage."""
        try:
            # Get the data manager
            if (
                DOMAIN not in self.hass.data
                or "data_manager" not in self.hass.data[DOMAIN]
            ):
                _LOGGER.warning("Data manager not available for sensor update")
                return

            data_manager = self.hass.data[DOMAIN]["data_manager"]

            # Get all readings for this entity
            readings = await data_manager.get_all_readings(self.entity_id)

            if not readings:
                _LOGGER.debug("No readings found for %s", self.entity_id)
                return

            # Find the latest cumulative reading
            cumulative_readings = [
                r for r in readings if r.reading_type.value == "cumulative"
            ]

            if not cumulative_readings:
                _LOGGER.debug("No cumulative readings found for %s", self.entity_id)
                return

            # Get the most recent reading by timestamp
            latest_reading = max(cumulative_readings, key=lambda r: r.timestamp)

            # Update the sensor value if it's different
            if self._attr_native_value != latest_reading.value:
                old_value = self._attr_native_value
                self._attr_native_value = latest_reading.value

                # Track last good value
                if latest_reading.value > 0:
                    self._last_good_value = latest_reading.value

                _LOGGER.debug(
                    "Sensor %s updated via async_update: %s -> %s (from reading at %s)",
                    self.entity_id,
                    old_value,
                    latest_reading.value,
                    latest_reading.timestamp,
                )
            else:
                _LOGGER.debug(
                    "Sensor %s value unchanged: %s",
                    self.entity_id,
                    self._attr_native_value,
                )

        except Exception as e:
            _LOGGER.error("Error updating sensor %s: %s", self.entity_id, e)
