"""Home Assistant for Garmin custom integration."""

from __future__ import annotations

import logging
from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import (
    GarminHomeAssistantBuilderView,
    GarminHomeAssistantConfigView,
    GarminHomeAssistantDashboardView,
    GarminHomeAssistantEntitiesView,
    GarminHomeAssistantGettingStartedView,
    GarminHomeAssistantSetupView,
    GarminHomeAssistantTemplatePreviewView,
)
from .const import DOMAIN
from .dashboard import async_setup_dashboard_store

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = []


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Home Assistant for Garmin integration."""
    hass.data.setdefault(DOMAIN, {})
    await async_setup_dashboard_store(hass)
    _async_register_view(hass)
    _async_register_panel(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Home Assistant for Garmin from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    _async_register_view(hass)
    _async_register_panel(hass)
    _LOGGER.info("Loaded Home Assistant for Garmin builder entry")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Home Assistant for Garmin config entry."""
    _LOGGER.info("Unloaded Home Assistant for Garmin builder entry")
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload a Home Assistant for Garmin config entry."""
    await async_unload_entry(hass, entry)
    return await async_setup_entry(hass, entry)


def _async_register_view(hass: HomeAssistant) -> None:
    """Register the GarminHomeAssistant companion endpoints once."""
    if hass.data[DOMAIN].get("view_registered"):
        return

    hass.http.register_view(GarminHomeAssistantConfigView)
    hass.http.register_view(GarminHomeAssistantSetupView)
    hass.http.register_view(GarminHomeAssistantDashboardView)
    hass.http.register_view(GarminHomeAssistantEntitiesView)
    hass.http.register_view(GarminHomeAssistantTemplatePreviewView)
    hass.http.register_view(GarminHomeAssistantBuilderView)
    hass.http.register_view(GarminHomeAssistantGettingStartedView)
    hass.data[DOMAIN]["view_registered"] = True
    _LOGGER.debug("Registered Home Assistant for Garmin API endpoints")


def _async_register_panel(hass: HomeAssistant) -> None:
    """Register the dashboard builder in the Home Assistant sidebar."""
    if hass.data[DOMAIN].get("panel_registered"):
        return

    frontend.async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title="Garmin",
        sidebar_icon="mdi:watch",
        frontend_url_path="homeassistant-garmin",
        config={
            "url": "/api/homeassistant_garmin/builder",
        },
        require_admin=False,
    )
    hass.data[DOMAIN]["panel_registered"] = True
    _LOGGER.debug("Registered Home Assistant for Garmin builder panel")
