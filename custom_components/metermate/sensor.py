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
    def native_value(self) -> float:
        """Return the state of the sensor."""
        if self._attr_native_value is None:
            return float(self._initial_reading)
        if isinstance(self._attr_native_value, (int, float)):
            return float(self._attr_native_value)
        return float(self._initial_reading)

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
        self._attr_native_value = new_value

        # Track last good value (any value > 0) for recovery purposes
        if new_value > 0:
            self._last_good_value = new_value

        _LOGGER.debug("Updating sensor value from %s to %s", old_value, new_value)
        _LOGGER.debug("Last good value updated to: %s", self._last_good_value)

        self.async_write_ha_state()
        _LOGGER.debug("State written to Home Assistant")
