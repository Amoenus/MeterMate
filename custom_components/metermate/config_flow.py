#!/usr/bin/env python3
"""Support for MeterMate config flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
    UnitOfEnergy,
    UnitOfVolume,
)
from homeassistant.helpers import selector
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import ATTR_INTEGRATION_NAME, CONF_INITIAL_READING, DEFAULT_NAME


class MeterMateFlowHandler(config_entries.ConfigFlow, domain=ATTR_INTEGRATION_NAME):
    """Config flow for MeterMate."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MeterMateOptionsFlowHandler:
        """Get the options flow for this handler."""
        return MeterMateOptionsFlowHandler(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors: dict[str, str] = {}

        if user_input is not None:
            # Validate device class and unit compatibility
            device_class = user_input.get(CONF_DEVICE_CLASS)
            unit = user_input.get(CONF_UNIT_OF_MEASUREMENT)

            if (
                device_class
                and unit
                and not self._validate_device_class_unit_compatibility(
                    device_class, unit
                )
            ):
                _errors["base"] = "incompatible_device_class_unit"

            # Validate initial reading is non-negative
            initial_reading = user_input.get(CONF_INITIAL_READING, 0)
            if initial_reading < 0:
                _errors[CONF_INITIAL_READING] = "negative_reading"

            if not _errors:
                # Convert enum device_class to string for proper serialization
                if device_class and hasattr(device_class, "value"):
                    user_input[CONF_DEVICE_CLASS] = device_class.value

                # Create unique ID based on the name
                unique_id = user_input[CONF_NAME].lower().replace(" ", "_")
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): TextSelector(
                        TextSelectorConfig(
                            type=TextSelectorType.TEXT, autocomplete="name"
                        )
                    ),
                    vol.Required(CONF_UNIT_OF_MEASUREMENT): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {
                                    "value": UnitOfEnergy.KILO_WATT_HOUR,
                                    "label": "kWh (Electricity)",
                                },
                                {
                                    "value": UnitOfEnergy.WATT_HOUR,
                                    "label": "Wh (Electricity)",
                                },
                                {
                                    "value": UnitOfEnergy.MEGA_WATT_HOUR,
                                    "label": "MWh (Electricity)",
                                },
                                {
                                    "value": UnitOfVolume.CUBIC_METERS,
                                    "label": "m³ (Gas/Water)",
                                },
                                {
                                    "value": UnitOfVolume.CUBIC_FEET,
                                    "label": "ft³ (Gas)",
                                },
                                {"value": UnitOfVolume.LITERS, "label": "L (Water)"},
                                {"value": UnitOfVolume.GALLONS, "label": "gal (Water)"},
                            ]
                        )
                    ),
                    vol.Required(CONF_DEVICE_CLASS): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": SensorDeviceClass.ENERGY, "label": "Energy"},
                                {"value": SensorDeviceClass.GAS, "label": "Gas"},
                                {"value": SensorDeviceClass.WATER, "label": "Water"},
                                {"value": SensorDeviceClass.VOLUME, "label": "Volume"},
                            ]
                        )
                    ),
                    vol.Optional(CONF_INITIAL_READING, default=0): vol.Coerce(float),
                }
            ),
            errors=_errors,
        )

    def _validate_device_class_unit_compatibility(
        self, device_class: str, unit: str
    ) -> bool:
        """Validate that device class and unit are compatible."""
        energy_units = {
            UnitOfEnergy.KILO_WATT_HOUR,
            UnitOfEnergy.WATT_HOUR,
            UnitOfEnergy.MEGA_WATT_HOUR,
        }
        volume_units = {
            UnitOfVolume.CUBIC_METERS,
            UnitOfVolume.CUBIC_FEET,
            UnitOfVolume.LITERS,
            UnitOfVolume.GALLONS,
        }

        if device_class == SensorDeviceClass.ENERGY:
            return unit in energy_units
        if device_class in (
            SensorDeviceClass.GAS,
            SensorDeviceClass.WATER,
            SensorDeviceClass.VOLUME,
        ):
            return unit in volume_units

        return True


class MeterMateOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle MeterMate options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        _errors: dict[str, str] = {}

        if user_input is not None:
            # Validate initial reading is non-negative
            initial_reading = user_input.get(CONF_INITIAL_READING, 0)
            if initial_reading < 0:
                _errors[CONF_INITIAL_READING] = "negative_reading"

            if not _errors:
                return self.async_create_entry(title="", data=user_input)

        # Pre-fill with current config values
        current_data = self.config_entry.data
        suggested_values = {
            CONF_INITIAL_READING: current_data.get(CONF_INITIAL_READING, 0),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        # Show current name as read-only
                        vol.Optional(CONF_NAME): TextSelector(
                            TextSelectorConfig(read_only=True)
                        ),
                        # Show current unit as read-only
                        vol.Optional(CONF_UNIT_OF_MEASUREMENT): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=[
                                    {
                                        "value": current_data[CONF_UNIT_OF_MEASUREMENT],
                                        "label": current_data[CONF_UNIT_OF_MEASUREMENT],
                                    }
                                ]
                            )
                        ),
                        # Show current device class as read-only
                        vol.Optional(CONF_DEVICE_CLASS): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=[
                                    {
                                        "value": current_data[CONF_DEVICE_CLASS],
                                        "label": current_data[
                                            CONF_DEVICE_CLASS
                                        ].title(),
                                    }
                                ]
                            )
                        ),
                        # Allow modification of initial reading
                        vol.Optional(CONF_INITIAL_READING, default=0): vol.Coerce(
                            float
                        ),
                    }
                ),
                {
                    CONF_NAME: current_data[CONF_NAME],
                    CONF_UNIT_OF_MEASUREMENT: current_data[CONF_UNIT_OF_MEASUREMENT],
                    CONF_DEVICE_CLASS: current_data[CONF_DEVICE_CLASS],
                    **suggested_values,
                },
            ),
            errors=_errors,
        )
