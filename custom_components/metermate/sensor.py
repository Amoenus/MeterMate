"""Sensor platform for MeterMate."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import CONF_NAME, CONF_UNIT_OF_MEASUREMENT
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_DEVICE_CLASS, CONF_INITIAL_READING, DOMAIN

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
        self._attr_unit_of_measurement = entry.data[CONF_UNIT_OF_MEASUREMENT]
        self._attr_device_class = entry.data[CONF_DEVICE_CLASS]
        self._initial_reading = entry.data.get(CONF_INITIAL_READING, 0)
        self._attr_native_value = 0.0

    @property
    def device_info(self) -> dict[str, any]:
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
            try:
                self._attr_native_value = float(last_state.state)
            except (ValueError, TypeError):
                self._attr_native_value = 0.0

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        return self._attr_native_value

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return extra state attributes."""
        return {
            "initial_reading": self._initial_reading,
            "integration": DOMAIN,
        }
