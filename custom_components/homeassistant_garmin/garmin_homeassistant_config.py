"""Generate GarminHomeAssistant-compatible dashboard JSON.

This module is a small translation layer from friendly Home Assistant
selections into the JSON format consumed by house-of-abbey/GarminHomeAssistant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


GARMIN_HOMEASSISTANT_SCHEMA = (
    "https://raw.githubusercontent.com/house-of-abbey/"
    "GarminHomeAssistant/main/config.schema.json"
)


@dataclass(slots=True)
class GarminDashboardItem:
    """A friendly builder item selected from Home Assistant."""

    entity_id: str
    name: str
    behavior: str = "auto"
    content: str | None = None
    title: str | None = None
    tap_action_action: str | None = None
    tap_action_data: dict[str, Any] | None = None
    confirm: bool | str = False
    pin: bool = False
    exit: bool = False
    enabled: bool = True
    numeric_min: int | float | None = None
    numeric_max: int | float | None = None
    numeric_step: int | float | None = None
    numeric_attribute: str | None = None
    numeric_data_attribute: str | None = None
    children: list["GarminDashboardItem"] = field(default_factory=list)


def build_dashboard_config(
    items: list[GarminDashboardItem],
    *,
    title: str = "Home",
    glance_content: str | None = None,
) -> dict[str, Any]:
    """Build a complete GarminHomeAssistant JSON document."""
    config: dict[str, Any] = {
        "$schema": GARMIN_HOMEASSISTANT_SCHEMA,
        "title": title,
        "items": [_build_item(item) for item in items],
    }

    if glance_content:
        config["glance"] = {
            "type": "info",
            "content": glance_content,
        }

    return config


def _build_item(item: GarminDashboardItem) -> dict[str, Any]:
    """Build one GarminHomeAssistant item."""
    behavior = _resolve_behavior(item)

    if behavior == "group":
        return _group_item(item)

    if behavior == "toggle":
        return _toggle_item(item)

    if behavior == "tap":
        return _tap_item(item)

    if behavior == "numeric":
        return _numeric_item(item)

    return _info_item(item)


def _resolve_behavior(item: GarminDashboardItem) -> str:
    """Infer a GarminHomeAssistant item type from entity domain."""
    if item.behavior != "auto":
        return item.behavior

    if item.children:
        return "group"

    domain = _domain(item.entity_id)

    if domain in {"light", "switch", "input_boolean"}:
        return "toggle"

    if domain in {"automation", "scene", "script"}:
        return "tap"

    if domain in {
        "input_number",
        "number",
        "fan",
        "valve",
        "cover",
        "media_player",
        "climate",
    }:
        return "numeric"

    return "info"


def _toggle_item(item: GarminDashboardItem) -> dict[str, Any]:
    output = {
        "entity": item.entity_id,
        "name": item.name,
        "type": "toggle",
    }
    _add_optional_common(output, item)
    return output


def _tap_item(item: GarminDashboardItem) -> dict[str, Any]:
    tap_action = {
        "action": item.tap_action_action or _tap_action(item.entity_id),
    }
    if item.tap_action_data:
        tap_action["data"] = item.tap_action_data

    output = {
        "name": item.name,
        "type": "tap",
        "tap_action": tap_action,
    }
    if item.entity_id:
        output["entity"] = item.entity_id
    _add_optional_common(output, item)
    _add_confirmation(output["tap_action"], item)
    return output


def _info_item(item: GarminDashboardItem) -> dict[str, Any]:
    output = {
        "name": item.name,
        "type": "info",
    }
    if item.content:
        output["content"] = item.content
    _add_enabled(output, item)
    return output


def _numeric_item(item: GarminDashboardItem) -> dict[str, Any]:
    domain = _domain(item.entity_id)
    action = f"{domain}.set_value"
    picker: dict[str, Any] = {
        "data_attribute": "value",
        "min": 0,
        "max": 100,
        "step": 1,
    }

    if domain == "light":
        action = "light.turn_on"
        picker = {
            "attribute": "brightness",
            "data_attribute": "brightness",
            "min": 0,
            "max": 255,
            "step": 5,
        }
    elif domain == "fan":
        action = "fan.set_percentage"
        picker = {
            "attribute": "percentage",
            "data_attribute": "percentage",
            "min": 0,
            "max": 100,
            "step": 5,
        }
    elif domain == "valve":
        action = "valve.set_valve_position"
        picker = {
            "attribute": "position",
            "data_attribute": "position",
            "min": 0,
            "max": 100,
            "step": 5,
        }
    elif domain == "cover":
        action = "cover.set_position"
        picker = {
            "attribute": "position",
            "data_attribute": "position",
            "min": 0,
            "max": 100,
            "step": 5,
        }
    elif domain == "media_player":
        action = "media_player.volume_set"
        picker = {
            "attribute": "volume_level",
            "data_attribute": "volume_level",
            "min": 0,
            "max": 1,
            "step": 0.05,
        }
    elif domain == "climate":
        action = "climate.set_temperature"
        picker = {
            "attribute": "temperature",
            "data_attribute": "temperature",
            "min": 50,
            "max": 85,
            "step": 1,
        }

    action = item.tap_action_action or action
    picker = _numeric_picker_with_overrides(picker, item)

    output = {
        "entity": item.entity_id,
        "name": item.name,
        "type": "numeric",
        "tap_action": {
            "action": action,
            "picker": picker,
        },
    }
    if item.tap_action_data:
        output["tap_action"]["data"] = item.tap_action_data
    if item.content:
        output["content"] = item.content
    _add_enabled(output, item)
    _add_confirmation(output["tap_action"], item)
    return output


def _group_item(item: GarminDashboardItem) -> dict[str, Any]:
    output = {
        "name": item.name,
        "title": item.title or item.name,
        "type": "group",
        "items": [_build_item(child) for child in item.children],
    }
    if item.content:
        output["content"] = item.content
    _add_enabled(output, item)
    return output


def _add_optional_common(output: dict[str, Any], item: GarminDashboardItem) -> None:
    if item.content:
        output["content"] = item.content
    _add_enabled(output, item)

    if item.confirm or item.pin or item.exit:
        output.setdefault("tap_action", {})
        _add_confirmation(output["tap_action"], item)


def _add_confirmation(tap_action: dict[str, Any], item: GarminDashboardItem) -> None:
    if item.pin:
        tap_action["pin"] = True
    elif item.confirm:
        tap_action["confirm"] = item.confirm

    if item.exit:
        tap_action["exit"] = True


def _add_enabled(output: dict[str, Any], item: GarminDashboardItem) -> None:
    if not item.enabled:
        output["enabled"] = False


def _tap_action(entity_id: str) -> str:
    domain = _domain(entity_id)

    if domain == "automation":
        return "automation.trigger"

    if domain == "scene":
        return "scene.turn_on"

    if domain == "script":
        return "script.turn_on"

    return f"{domain}.toggle"


def _numeric_picker_with_overrides(
    picker: dict[str, Any],
    item: GarminDashboardItem,
) -> dict[str, Any]:
    output = dict(picker)

    if item.numeric_min is not None:
        output["min"] = item.numeric_min
    if item.numeric_max is not None:
        output["max"] = item.numeric_max
    if item.numeric_step is not None:
        output["step"] = item.numeric_step
    if item.numeric_attribute:
        output["attribute"] = item.numeric_attribute
    if item.numeric_data_attribute:
        output["data_attribute"] = item.numeric_data_attribute

    return output


def _default_content(entity_id: str) -> str:
    return "{{ states('" + entity_id + "') }}"


def _domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0]
