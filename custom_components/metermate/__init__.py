"""
MeterMate integration for Home Assistant.

For more details about this integration, please refer to
https://github.com/Amoenus/metermate
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform

from .const import DOMAIN
from .services import async_setup_services, async_unload_services

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from .data import MeterMateConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # noqa: ARG001
    """Set up the MeterMate integration."""
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MeterMateConfigEntry) -> bool:
    """Set up MeterMate from a config entry."""
    # Initialize domain data if not present
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Initialize entity registry for our domain
    if "entities" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entities"] = {}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MeterMateConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await async_unload_services(hass)
    return unload_ok
