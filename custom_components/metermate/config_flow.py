#!/usr/bin/env python3
"""Support for MeterMate config flow."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_UNIT_OF_MEASUREMENT
from homeassistant.helpers import selector

from .const import CONF_DEVICE_CLASS, CONF_INITIAL_READING, DEFAULT_NAME, DOMAIN


class MeterMateFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
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
                                {"value": "kWh", "label": "kWh (Electricity)"},
                                {"value": "Wh", "label": "Wh (Electricity)"},
                                {"value": "MWh", "label": "MWh (Electricity)"},
                                {"value": "m³", "label": "m³ (Gas/Water)"},
                                {"value": "ft³", "label": "ft³ (Gas)"},
                                {"value": "L", "label": "L (Water)"},
                                {"value": "gal", "label": "gal (Water)"},
                            ]
                        )
                    ),
                    vol.Required(CONF_DEVICE_CLASS): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "energy", "label": "Energy"},
                                {"value": "gas", "label": "Gas"},
                                {"value": "water", "label": "Water"},
                                {"value": "volume", "label": "Volume"},
                            ]
                        )
                    ),
                    vol.Optional(CONF_INITIAL_READING, default=0): vol.Coerce(float),
                }
            ),
            errors=_errors,
        )
