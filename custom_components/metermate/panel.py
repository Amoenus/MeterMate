"""Panel for MeterMate integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import callback

from .const import ATTR_INTEGRATION_NAME

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PANEL_URL = "/metermate-panel"
PANEL_TITLE = "MeterMate"
PANEL_ICON = "mdi:counter"
PANEL_FILENAME = "index.html"


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the MeterMate panel."""
    if ATTR_INTEGRATION_NAME not in hass.data:
        _LOGGER.error("MeterMate domain not found in hass.data")
        return

    # Get the path to our frontend files
    frontend_path = Path(__file__).parent / "frontend"

    # Register the static path for frontend files
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path="/metermate", path=str(frontend_path), cache_headers=False
            )
        ]
    )

    # Register the panel using panel_custom approach
    from homeassistant.components.panel_custom import async_register_panel

    await async_register_panel(
        hass,
        frontend_url_path="metermate-panel",
        webcomponent_name="metermate-panel",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url="/metermate/src/components/metermate-panel.js",
        config={"title": "MeterMate - Manual Utility Readings"},
        require_admin=False,
    )

    _LOGGER.debug("MeterMate panel registered successfully")


@callback
def async_unregister_panel(hass: HomeAssistant) -> None:  # noqa: ARG001
    """Unregister the MeterMate panel."""
    # Note: Built-in panels are automatically cleaned up
    _LOGGER.debug("MeterMate panel unregistered")
