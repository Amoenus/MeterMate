#!/usr/bin/env python3
"""Support for MeterMate config flow."""

from __future__ import annotations

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

from .const import ATTR_INTEGRATION_NAME, CONF_INITIAL_READING, DEFAULT_NAME


class MeterMateFlowHandler(config_entries.ConfigFlow, domain=ATTR_INTEGRATION_NAME):
    """Config flow for MeterMate."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}

        if user_input is not None:
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
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
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
