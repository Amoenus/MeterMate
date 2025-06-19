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

    def __init__(self) -> None:
        """Initialize config flow."""
        self._device_class: str | None = None

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
        """Handle a flow initialized by the user - first step to select device class."""
        _errors: dict[str, str] = {}

        if user_input is not None:
            device_class = user_input.get(CONF_DEVICE_CLASS)
            if device_class and hasattr(device_class, "value"):
                self._device_class = device_class.value
            else:
                self._device_class = device_class

            return await self.async_step_meter_config()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_CLASS): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {
                                    "value": SensorDeviceClass.ENERGY,
                                    "label": "Energy (Electricity)",
                                },
                                {"value": SensorDeviceClass.GAS, "label": "Gas"},
                                {"value": SensorDeviceClass.WATER, "label": "Water"},
                                {
                                    "value": SensorDeviceClass.VOLUME,
                                    "label": "Volume (Other liquids)",
                                },
                            ]
                        )
                    ),
                }
            ),
            errors=_errors,
        )

    async def async_step_meter_config(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle meter configuration with device class specific units."""
        _errors: dict[str, str] = {}

        if user_input is not None:
            # Validate initial reading is non-negative
            initial_reading = user_input.get(CONF_INITIAL_READING, 0)
            if initial_reading < 0:
                _errors[CONF_INITIAL_READING] = "negative_reading"

            if not _errors:
                # Combine with device class from previous step
                complete_data = {
                    CONF_DEVICE_CLASS: self._device_class,
                    **user_input,
                }

                # Create unique ID based on the name
                unique_id = user_input[CONF_NAME].lower().replace(" ", "_")
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=complete_data,
                )

        # Get unit options based on device class
        unit_options = self._get_unit_options_for_device_class(self._device_class or "")

        return self.async_show_form(
            step_id="meter_config",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): TextSelector(
                        TextSelectorConfig(
                            type=TextSelectorType.TEXT, autocomplete="name"
                        )
                    ),
                    vol.Required(CONF_UNIT_OF_MEASUREMENT): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=unit_options)  # type: ignore[arg-type]
                    ),
                    vol.Optional(CONF_INITIAL_READING, default=0): vol.Coerce(float),
                }
            ),
            errors=_errors,
        )

    def _get_unit_options_for_device_class(
        self, device_class: str
    ) -> list[dict[str, Any]]:
        """Get appropriate unit options based on device class."""
        if device_class == SensorDeviceClass.ENERGY:
            return [
                {"value": UnitOfEnergy.KILO_WATT_HOUR, "label": "kWh (Kilowatt hours)"},
                {"value": UnitOfEnergy.WATT_HOUR, "label": "Wh (Watt hours)"},
                {"value": UnitOfEnergy.MEGA_WATT_HOUR, "label": "MWh (Megawatt hours)"},
            ]
        if device_class == SensorDeviceClass.GAS:
            return [
                {"value": UnitOfVolume.CUBIC_METERS, "label": "m³ (Cubic meters)"},
                {"value": UnitOfVolume.CUBIC_FEET, "label": "ft³ (Cubic feet)"},
            ]
        if device_class == SensorDeviceClass.WATER:
            return [
                {"value": UnitOfVolume.CUBIC_METERS, "label": "m³ (Cubic meters)"},
                {"value": UnitOfVolume.LITERS, "label": "L (Liters)"},
                {"value": UnitOfVolume.GALLONS, "label": "gal (Gallons)"},
            ]
        if device_class == SensorDeviceClass.VOLUME:
            return [
                {"value": UnitOfVolume.CUBIC_METERS, "label": "m³ (Cubic meters)"},
                {"value": UnitOfVolume.CUBIC_FEET, "label": "ft³ (Cubic feet)"},
                {"value": UnitOfVolume.LITERS, "label": "L (Liters)"},
                {"value": UnitOfVolume.GALLONS, "label": "gal (Gallons)"},
            ]

        # Fallback to all units
        return [
            {"value": UnitOfEnergy.KILO_WATT_HOUR, "label": "kWh (Kilowatt hours)"},
            {"value": UnitOfEnergy.WATT_HOUR, "label": "Wh (Watt hours)"},
            {"value": UnitOfEnergy.MEGA_WATT_HOUR, "label": "MWh (Megawatt hours)"},
            {"value": UnitOfVolume.CUBIC_METERS, "label": "m³ (Cubic meters)"},
            {"value": UnitOfVolume.CUBIC_FEET, "label": "ft³ (Cubic feet)"},
            {"value": UnitOfVolume.LITERS, "label": "L (Liters)"},
            {"value": UnitOfVolume.GALLONS, "label": "gal (Gallons)"},
        ]


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
