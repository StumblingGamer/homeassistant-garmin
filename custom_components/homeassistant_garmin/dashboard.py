"""Stored GarminHomeAssistant dashboard model."""

from __future__ import annotations

import secrets
import string
from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

DASHBOARD_STORAGE_KEY = f"{DOMAIN}.dashboard"
DASHBOARD_STORAGE_VERSION = 1

CODE_LENGTH = 8
CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_setup_code() -> str:
    """Generate a short setup code for public config URLs."""
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def default_dashboard() -> dict[str, Any]:
    """Return a new empty dashboard document."""
    return {
        "version": 1,
        "setup_code": generate_setup_code(),
        "title": "Home Assistant",
        "base_url": "",
        "glance": {
            "type": "status",
            "content": "",
        },
        "items": [],
    }


async def async_setup_dashboard_store(hass: HomeAssistant) -> None:
    """Create and load the dashboard storage object."""
    hass.data.setdefault(DOMAIN, {})
    store = Store(hass, DASHBOARD_STORAGE_VERSION, DASHBOARD_STORAGE_KEY)
    hass.data[DOMAIN]["dashboard_store"] = store

    dashboard = await store.async_load()
    if dashboard is None:
        dashboard = default_dashboard()
        await store.async_save(dashboard)

    hass.data[DOMAIN]["dashboard"] = normalize_dashboard(dashboard)


async def async_get_dashboard(hass: HomeAssistant) -> dict[str, Any]:
    """Return the current dashboard document."""
    dashboard = hass.data.setdefault(DOMAIN, {}).get("dashboard")
    if dashboard is None:
        await async_setup_dashboard_store(hass)
        dashboard = hass.data[DOMAIN]["dashboard"]

    return deepcopy(dashboard)


async def async_save_dashboard(
    hass: HomeAssistant,
    dashboard: dict[str, Any],
) -> dict[str, Any]:
    """Normalize, store, and return the dashboard document."""
    normalized = normalize_dashboard(dashboard)
    hass.data.setdefault(DOMAIN, {})["dashboard"] = normalized
    await hass.data[DOMAIN]["dashboard_store"].async_save(normalized)
    return deepcopy(normalized)


def normalize_dashboard(dashboard: dict[str, Any]) -> dict[str, Any]:
    """Return a dashboard document with required fields and stable item ids."""
    current = default_dashboard()
    current.update({key: value for key, value in dashboard.items() if value is not None})
    current["setup_code"] = str(current.get("setup_code") or generate_setup_code()).upper()
    current["title"] = str(current.get("title") or "Home Assistant")
    current["base_url"] = str(current.get("base_url") or "").rstrip("/")
    current["glance"] = _normalize_glance(current.get("glance"))
    current["items"] = _normalize_items(current.get("items", []))
    return current


def _normalize_glance(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {"type": "status", "content": ""}

    glance_type = str(value.get("type") or "status")
    if glance_type not in {"status", "info"}:
        glance_type = "status"

    return {
        "type": glance_type,
        "content": str(value.get("content") or ""),
    }


def _normalize_items(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue

        item_type = str(item.get("type") or "auto")
        if item_type not in {"auto", "toggle", "tap", "info", "numeric", "group"}:
            item_type = "auto"

        entity_id = str(item.get("entity_id") or item.get("entity") or "")
        name = str(item.get("name") or entity_id or "Group")
        normalized_item: dict[str, Any] = {
            "id": str(item.get("id") or generate_setup_code()),
            "type": item_type,
            "entity_id": entity_id,
            "name": name,
            "title": str(item.get("title") or name),
            "content": str(item.get("content") or ""),
            "tap_action_action": str(item.get("tap_action_action") or ""),
            "tap_action_data": str(item.get("tap_action_data") or ""),
            "confirm": _normalize_confirm(item.get("confirm", False)),
            "pin": bool(item.get("pin", False)),
            "exit": bool(item.get("exit", False)),
            "enabled": bool(item.get("enabled", True)),
            "numeric_min": _optional_number(item.get("numeric_min")),
            "numeric_max": _optional_number(item.get("numeric_max")),
            "numeric_step": _optional_number(item.get("numeric_step")),
            "numeric_attribute": str(item.get("numeric_attribute") or ""),
            "numeric_data_attribute": str(item.get("numeric_data_attribute") or ""),
            "items": _normalize_items(item.get("items", [])),
        }
        normalized.append(normalized_item)

    return normalized


def _normalize_confirm(value: Any) -> bool | str:
    if isinstance(value, bool):
        return value

    value_text = str(value or "").strip()
    return value_text or False


def _optional_number(value: Any) -> int | float | None:
    if value in (None, ""):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if number.is_integer():
        return int(number)

    return number
