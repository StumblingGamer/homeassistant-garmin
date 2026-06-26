"""Constants for Home Assistant for Garmin."""

from __future__ import annotations

DOMAIN = "homeassistant_garmin"
NAME = "Home Assistant for Garmin"

CONF_ENTITY_ID = "entity_id"
CONF_TITLE = "title"
CONF_WATCH_BEHAVIOR = "watch_behavior"
CONF_CONTENT_TEMPLATE = "content"
CONF_CONFIRM = "confirm"
CONF_PIN = "pin"
CONF_ENABLED = "enabled"
CONF_EXIT = "exit"

DEFAULT_TITLE = "Home Assistant"
DEFAULT_WATCH_BEHAVIOR = "auto"

WATCH_BEHAVIOR_AUTO = "auto"
WATCH_BEHAVIOR_TOGGLE = "toggle"
WATCH_BEHAVIOR_TAP = "tap"
WATCH_BEHAVIOR_INFO = "info"
WATCH_BEHAVIOR_NUMERIC = "numeric"
WATCH_BEHAVIOR_GROUP = "group"

WATCH_BEHAVIOR_OPTIONS = (
    WATCH_BEHAVIOR_AUTO,
    WATCH_BEHAVIOR_TOGGLE,
    WATCH_BEHAVIOR_TAP,
    WATCH_BEHAVIOR_INFO,
    WATCH_BEHAVIOR_NUMERIC,
)

GARMIN_HOMEASSISTANT_CONFIG_PATH = (
    "/api/homeassistant_garmin/garminhomeassistant/config/{setup_code}"
)
GARMIN_HOMEASSISTANT_SETUP_PATH = (
    "/api/homeassistant_garmin/garminhomeassistant/setup/{setup_code}"
)
GARMIN_HOMEASSISTANT_BUILDER_PATH = "/api/homeassistant_garmin/builder"
GARMIN_HOMEASSISTANT_DASHBOARD_PATH = "/api/homeassistant_garmin/dashboard"
GARMIN_HOMEASSISTANT_ENTITIES_PATH = "/api/homeassistant_garmin/entities"
GARMIN_HOMEASSISTANT_TEMPLATE_PREVIEW_PATH = "/api/homeassistant_garmin/template_preview"
GARMIN_HOMEASSISTANT_VALIDATE_PATH = "/api/homeassistant_garmin/garminhomeassistant/validate"
