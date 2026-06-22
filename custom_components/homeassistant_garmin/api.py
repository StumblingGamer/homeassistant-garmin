"""HTTP API for Home Assistant for Garmin."""

from __future__ import annotations

from html import escape
import logging

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.json import json_dumps

from .const import (
    DOMAIN,
    GARMIN_HOMEASSISTANT_BUILDER_PATH,
    GARMIN_HOMEASSISTANT_CONFIG_PATH,
    GARMIN_HOMEASSISTANT_DASHBOARD_PATH,
    GARMIN_HOMEASSISTANT_ENTITIES_PATH,
    GARMIN_HOMEASSISTANT_SETUP_PATH,
    GARMIN_HOMEASSISTANT_TEMPLATE_PREVIEW_PATH,
)
from .dashboard import async_get_dashboard, async_save_dashboard
from .garmin_homeassistant_config import GarminDashboardItem, build_dashboard_config

_LOGGER = logging.getLogger(__name__)


class GarminHomeAssistantConfigView(HomeAssistantView):
    """Publish JSON menu config for the upstream GarminHomeAssistant app."""

    url = GARMIN_HOMEASSISTANT_CONFIG_PATH
    name = f"api:{DOMAIN}:garminhomeassistant_config"
    requires_auth = False

    async def get(self, request: web.Request, setup_code: str) -> web.Response:
        """Return a GarminHomeAssistant-compatible dashboard config."""
        hass: HomeAssistant = request.app["hass"]
        dashboard = await async_get_dashboard(hass)

        if setup_code.upper() == dashboard["setup_code"]:
            items = _dashboard_garmin_items(hass, dashboard.get("items", []))
            if not items:
                return _json_error("no_items", "No Garmin dashboard items are available", 404)

            glance = dashboard.get("glance", {})
            glance_content = None
            if glance.get("type") == "info" and glance.get("content"):
                glance_content = str(glance["content"])

            return _json_response(
                build_dashboard_config(
                    items,
                    title=str(dashboard.get("title") or "Home Assistant"),
                    glance_content=glance_content,
                )
            )

        _LOGGER.warning(
            "Invalid Home Assistant for Garmin configuration key used for GarminHomeAssistant config"
        )
        return _json_error("invalid_config_key", "Invalid configuration key", 404)


class GarminHomeAssistantSetupView(HomeAssistantView):
    """Show mobile-friendly GarminHomeAssistant setup values."""

    url = GARMIN_HOMEASSISTANT_SETUP_PATH
    name = f"api:{DOMAIN}:garminhomeassistant_setup"
    requires_auth = False

    async def get(self, request: web.Request, setup_code: str) -> web.Response:
        """Return a small setup page users can open on their phone."""
        hass: HomeAssistant = request.app["hass"]
        dashboard = await async_get_dashboard(hass)

        if setup_code.upper() != dashboard["setup_code"]:
            _LOGGER.warning(
                "Invalid Home Assistant for Garmin configuration key used for setup"
            )
            return _json_error("invalid_config_key", "Invalid configuration key", 404)

        public_base_url = await _async_public_base_url(hass, request, dashboard)
        api_url = f"{public_base_url}/api"
        config_url = (
            f"{public_base_url}/api/homeassistant_garmin/"
            f"garminhomeassistant/config/{setup_code.upper()}"
        )

        return web.Response(
            text=_setup_html(api_url, config_url),
            content_type="text/html",
        )


class GarminHomeAssistantDashboardView(HomeAssistantView):
    """API for the dashboard builder."""

    url = GARMIN_HOMEASSISTANT_DASHBOARD_PATH
    name = f"api:{DOMAIN}:garminhomeassistant_dashboard"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Return the stored dashboard document."""
        return _json_response(await async_get_dashboard(request.app["hass"]))

    async def post(self, request: web.Request) -> web.Response:
        """Replace the stored dashboard document."""
        try:
            data = await request.json()
        except ValueError:
            return _json_error("bad_request", "Expected JSON body", 400)

        current = await async_get_dashboard(request.app["hass"])
        if str(data.get("setup_code", "")).upper() != current["setup_code"]:
            return _json_error("invalid_setup_code", "Invalid setup code", 403)

        dashboard = await async_save_dashboard(request.app["hass"], data)
        return _json_response(dashboard)


class GarminHomeAssistantBuilderView(HomeAssistantView):
    """Minimal dashboard builder page."""

    url = GARMIN_HOMEASSISTANT_BUILDER_PATH
    name = f"api:{DOMAIN}:garminhomeassistant_builder"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Return the builder HTML."""
        dashboard = await async_get_dashboard(request.app["hass"])
        base_url = await _async_public_base_url(request.app["hass"], request, dashboard)
        return web.Response(
            text=_builder_html(dashboard, base_url),
            content_type="text/html",
        )


class GarminHomeAssistantGettingStartedView(HomeAssistantView):
    """Show beginner-friendly setup help."""

    url = "/api/homeassistant_garmin/docs/getting-started"
    name = f"api:{DOMAIN}:garminhomeassistant_getting_started"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Return the getting started guide."""
        return web.Response(
            text=_getting_started_html(),
            content_type="text/html",
        )


class GarminHomeAssistantEntitiesView(HomeAssistantView):
    """Return entity metadata for the dashboard builder picker."""

    url = GARMIN_HOMEASSISTANT_ENTITIES_PATH
    name = f"api:{DOMAIN}:garminhomeassistant_entities"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Return current Home Assistant entities for picker UI."""
        hass: HomeAssistant = request.app["hass"]
        try:
            from homeassistant.helpers import area_registry as ar
            from homeassistant.helpers import device_registry as dr
            from homeassistant.helpers import entity_registry as er

            area_registry = ar.async_get(hass)
            device_registry = dr.async_get(hass)
            entity_registry = er.async_get(hass)
        except Exception:  # noqa: BLE001 - registry helpers vary by HA version
            area_registry = None
            device_registry = None
            entity_registry = None

        entities = []
        for state in hass.states.async_all():
            entity_entry = (
                entity_registry.async_get(state.entity_id)
                if entity_registry is not None
                else None
            )
            device_entry = (
                device_registry.async_get(entity_entry.device_id)
                if device_registry is not None
                and entity_entry is not None
                and entity_entry.device_id
                else None
            )
            area_id = None
            if entity_entry is not None:
                area_id = entity_entry.area_id
            if not area_id and device_entry is not None:
                area_id = device_entry.area_id
            area = (
                area_registry.async_get_area(area_id)
                if area_registry is not None and area_id
                else None
            )
            entities.append(
                {
                    "entity_id": state.entity_id,
                    "name": str(
                        state.attributes.get(ATTR_FRIENDLY_NAME, state.entity_id)
                    ),
                    "domain": state.domain,
                    "area": area.name if area is not None else "",
                    "device_class": str(state.attributes.get("device_class") or ""),
                    "icon": str(state.attributes.get("icon") or ""),
                }
            )

        entities.sort(key=lambda item: (item["area"], item["domain"], item["name"].lower()))
        return _json_response({"entities": entities})


class GarminHomeAssistantTemplatePreviewView(HomeAssistantView):
    """Render a Home Assistant template for the dashboard builder."""

    url = GARMIN_HOMEASSISTANT_TEMPLATE_PREVIEW_PATH
    name = f"api:{DOMAIN}:garminhomeassistant_template_preview"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        """Render a Jinja template after checking the dashboard setup code."""
        hass: HomeAssistant = request.app["hass"]
        try:
            data = await request.json()
        except ValueError:
            return _json_error("bad_request", "Expected JSON body", 400)

        dashboard = await async_get_dashboard(hass)
        if str(data.get("setup_code", "")).upper() != dashboard["setup_code"]:
            return _json_error("invalid_setup_code", "Invalid setup code", 403)

        template_text = str(data.get("template") or "")
        if not template_text:
            return _json_response({"result": ""})

        try:
            from homeassistant.helpers.template import Template

            template = Template(template_text, hass)
            result = template.async_render(parse_result=False)
        except Exception as err:  # noqa: BLE001 - template errors should be shown in UI
            return _json_response(
                {
                    "error": "template_error",
                    "message": str(err),
                },
                status=400,
            )

        return _json_response({"result": str(result)})


def _json_response(payload: dict, status: int = 200) -> web.Response:
    """Return a JSON response using Home Assistant's JSON encoder."""
    return web.Response(
        text=json_dumps(payload),
        status=status,
        content_type="application/json",
    )


def _json_error(code: str, message: str, status: int) -> web.Response:
    """Return a small Garmin-friendly error payload."""
    return _json_response(
        {
            "error": code,
            "message": message,
        },
        status=status,
    )


def _dashboard_garmin_items(
    hass: HomeAssistant,
    dashboard_items: list[dict],
) -> list[GarminDashboardItem]:
    """Convert the stored dashboard tree to GarminHomeAssistant items."""
    items: list[GarminDashboardItem] = []
    for item in dashboard_items:
        item_type = str(item.get("type") or "auto")
        children = _dashboard_garmin_items(hass, item.get("items", []))
        entity_id = str(item.get("entity_id") or "")
        state = hass.states.get(entity_id) if entity_id else None

        has_custom_tap_action = item_type == "tap" and item.get("tap_action_action")
        if item_type != "group" and not has_custom_tap_action and (not entity_id or state is None):
            continue

        behavior = item_type
        if behavior == "auto" and state is not None:
            behavior = _inferred_garmin_homeassistant_behavior(state)

        content = str(item.get("content") or "")
        if not content and state is not None:
            content = _garmin_homeassistant_content(state)

        items.append(
            GarminDashboardItem(
                entity_id=entity_id,
                name=str(item.get("name") or entity_id or "Group"),
                behavior=behavior,
                content=content,
                title=str(item.get("title") or item.get("name") or "Group"),
                tap_action_action=str(item.get("tap_action_action") or ""),
                tap_action_data=_parse_json_object(
                    str(item.get("tap_action_data") or "")
                ),
                confirm=item.get("confirm", False),
                pin=bool(item.get("pin", False)),
                exit=bool(item.get("exit", False)),
                enabled=bool(item.get("enabled", True)),
                numeric_min=item.get("numeric_min"),
                numeric_max=item.get("numeric_max"),
                numeric_step=item.get("numeric_step"),
                numeric_attribute=str(item.get("numeric_attribute") or ""),
                numeric_data_attribute=str(item.get("numeric_data_attribute") or ""),
                children=children,
            )
        )

    return items


def _parse_json_object(value: str) -> dict | None:
    """Parse optional action data JSON for GarminHomeAssistant."""
    if not value.strip():
        return None

    try:
        import json

        parsed = json.loads(value)
    except ValueError:
        _LOGGER.warning("Ignoring invalid GarminHomeAssistant action data JSON")
        return None

    if not isinstance(parsed, dict):
        _LOGGER.warning("Ignoring GarminHomeAssistant action data that is not an object")
        return None

    return parsed


def _inferred_garmin_homeassistant_behavior(state: State) -> str:
    """Infer an upstream GarminHomeAssistant item type from an entity state."""
    if state.domain in {"switch", "input_boolean", "light"}:
        return "toggle"

    if state.domain in {"automation", "scene", "script"}:
        return "tap"

    if state.domain in {"input_number", "number"}:
        return "numeric"

    return "info"


def _garmin_homeassistant_content(state: State) -> str:
    """Return a compact template for GarminHomeAssistant item subtitles."""
    return "{{ states('" + state.entity_id + "') }}"


def _request_base_url(request: web.Request) -> str:
    """Build the public base URL from the current request."""
    return f"{request.scheme}://{request.host}".rstrip("/")


async def _async_public_base_url(
    hass: HomeAssistant,
    request: web.Request,
    dashboard: dict,
) -> str:
    """Return the best external URL for GarminHomeAssistant setup."""
    stored_url = str(dashboard.get("base_url") or "").rstrip("/")
    if stored_url:
        return stored_url

    cloud_url = await _async_cloud_remote_url(hass)
    if cloud_url:
        return cloud_url.rstrip("/")

    try:
        from homeassistant.helpers.network import get_url

        external_url = get_url(hass, prefer_external=True, allow_internal=False)
    except Exception as err:  # noqa: BLE001 - network helpers vary by HA version
        _LOGGER.debug("Could not discover Home Assistant external URL: %s", err)
        external_url = None

    if external_url:
        return str(external_url).rstrip("/")

    return _request_base_url(request)


async def _async_cloud_remote_url(hass: HomeAssistant) -> str | None:
    """Return Home Assistant Cloud remote UI URL when available."""
    try:
        from homeassistant.components import cloud

        if hasattr(cloud, "async_remote_ui_url"):
            url = await cloud.async_remote_ui_url(hass)
            if url:
                return str(url)
    except Exception as err:  # noqa: BLE001 - cloud is optional and versioned
        _LOGGER.debug("Could not discover Home Assistant Cloud URL: %s", err)

    cloud_data = hass.data.get("cloud")
    for attr_name in ("remote_ui_url", "remote_url"):
        url = getattr(cloud_data, attr_name, None)
        if url:
            return str(url)

    return None


def _setup_html(api_url: str, config_url: str) -> str:
    """Build a simple phone-friendly setup page."""
    api_url = escape(api_url)
    config_url = escape(config_url)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GarminHomeAssistant Setup</title>
  <style>
    body {{
      background: #111;
      color: #f5f5f5;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
      margin: 0;
      padding: 20px 20px 96px;
    }}
    main {{
      margin: 0 auto;
      max-width: 720px;
    }}
    h1 {{
      font-size: 1.5rem;
      margin: 0 0 1rem;
    }}
    label {{
      color: #b8c0cc;
      display: block;
      font-size: .86rem;
      margin: 1.2rem 0 .35rem;
    }}
    input {{
      background: #1e1e1e;
      border: 1px solid #555;
      border-radius: 6px;
      box-sizing: border-box;
      color: #fff;
      font: inherit;
      padding: .7rem;
      width: 100%;
    }}
    p {{
      color: #d5d9df;
    }}
    .note {{
      background: #20242b;
      border-left: 4px solid #03a9f4;
      margin-top: 1.2rem;
      padding: .8rem;
    }}
  </style>
</head>
<body>
  <main id="top">
    <h1>GarminHomeAssistant Setup</h1>
    <p>Install GarminHomeAssistant from Connect IQ, then copy these values into its app settings on your phone.</p>

    <label for="api-url">API URL</label>
    <input id="api-url" readonly value="{api_url}" onclick="this.select()">

    <label for="config-url">Configuration URL</label>
    <input id="config-url" readonly value="{config_url}" onclick="this.select()">

    <label for="api-key">API key</label>
    <input id="api-key" readonly value="Create a Home Assistant long-lived access token">

    <div class="note">
      To create the API key, open your Home Assistant user profile, create a
      long-lived access token named GarminHomeAssistant, copy it immediately,
      and paste it into the GarminHomeAssistant API key field.
    </div>
  </main>
</body>
</html>"""


def _getting_started_html() -> str:
    """Build a beginner-friendly setup guide."""
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Home Assistant for Garmin - Getting Started</title>
  <style>
    body { background:#111; color:#f5f5f5; font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; line-height:1.5; margin:0; padding:20px; }
    main { margin:0 auto; max-width:820px; }
    a { color:#8bdcff; }
    code { background:#252525; border-radius:4px; padding:.1rem .3rem; }
    li { margin:.35rem 0; }
    .note { background:#20242b; border-left:4px solid #03a9f4; margin:1rem 0; padding:.8rem; }
  </style>
</head>
<body>
  <main>
    <h1>Getting Started</h1>
    <p><a href="/api/homeassistant_garmin/builder">Back to builder</a></p>
    <div class="note">
      This integration is a companion setup builder for
      <a href="https://apps.garmin.com/en-US/apps/61c91d28-ec5e-438d-9f83-39e9f45b199d">GarminHomeAssistant</a>.
    </div>
    <p>
      <a href="#overview">Overview</a> |
      <a href="#needs">What you need</a> |
      <a href="#url">External URL</a> |
      <a href="#settings">Watch settings</a> |
      <a href="#first-item">First item</a> |
      <a href="#number-picker">Number picker</a> |
      <a href="#troubleshooting">Troubleshooting</a>
    </p>
    <h2 id="overview">Overview</h2>
    <p>
      There are three pieces: Home Assistant for Garmin builds the menu,
      GarminHomeAssistant runs on the watch, and Garmin Connect / Connect IQ on
      your phone stores the app settings.
    </p>
    <p>
      The watch app needs an API URL, a Configuration URL, and a Home Assistant
      long-lived access token. The builder generates the URLs. You create the
      token from your Home Assistant user profile.
    </p>
    <p><a href="#top">Back to top</a> | <a href="/api/homeassistant_garmin/builder">Back to builder</a></p>
    <h2 id="needs">What you need</h2>
    <ol>
      <li>This Home Assistant custom integration installed and added.</li>
      <li>The GarminHomeAssistant app installed from Connect IQ on your watch.</li>
      <li>A Home Assistant URL your phone can reach while the watch app runs.</li>
      <li>A Home Assistant long-lived access token for the Garmin app.</li>
    </ol>
    <p>If the Garmin sidebar item does not appear after adding the integration, hard refresh Home Assistant and restart once more after copying files.</p>
    <p><a href="#top">Back to top</a> | <a href="/api/homeassistant_garmin/builder">Back to builder</a></p>
    <h2 id="url">External URL options</h2>
    <p>GarminHomeAssistant communicates through the phone, so the URL must work from the phone's network path.</p>
    <ul>
      <li><strong>Nabu Casa / Home Assistant Cloud</strong> is the easiest paid option.</li>
      <li><strong>Your own HTTPS reverse proxy</strong> can work if it uses a publicly trusted certificate.</li>
      <li><strong>Cloudflare Tunnel or similar</strong> can work when configured with the headers and settings GarminHomeAssistant expects.</li>
      <li><strong>VPN</strong> can work if the phone is connected to that VPN when using the watch app.</li>
    </ul>
    <p>Good examples: <code>https://example.ui.nabu.casa</code> or <code>https://ha.example.com</code>.</p>
    <p>Local URLs such as <code>http://homeassistant.local:8123</code> may fail away from home, across VLANs, on guest Wi-Fi, or on cellular.</p>
    <p><a href="#top">Back to top</a> | <a href="/api/homeassistant_garmin/builder">Back to builder</a></p>
    <h2 id="settings">Watch app settings</h2>
    <ol>
      <li>Open <strong>Garmin</strong> from the Home Assistant sidebar.</li>
      <li>Open <strong>Watch App Settings</strong>.</li>
      <li>Copy the API URL and Configuration URL into GarminHomeAssistant settings.</li>
      <li>Create a long-lived access token from your Home Assistant profile.</li>
      <li>Paste that token into the GarminHomeAssistant API key setting.</li>
    </ol>
    <p>Home Assistant only shows a long-lived token once. If you lose it, delete it and create a new one.</p>
    <p><a href="#top">Back to top</a> | <a href="/api/homeassistant_garmin/builder">Back to builder</a></p>
    <h2 id="first-item">Build your first item</h2>
    <ol>
      <li>In <strong>Add Item</strong>, search for a simple entity such as a light or switch.</li>
      <li>Let the watch name auto-fill, or edit it.</li>
      <li>Leave Behavior on <strong>Automatic</strong> for the first test.</li>
      <li>Select <strong>Add item</strong>.</li>
      <li>Use the sticky <strong>Save dashboard</strong> bar when it appears.</li>
      <li>Open or reopen GarminHomeAssistant on the watch.</li>
    </ol>
    <p>If the item is in the builder but not on the watch, open <strong>View Garmin JSON</strong>. If it is in that JSON, reopen the watch app or resync app settings from the phone.</p>
    <p><a href="#top">Back to top</a> | <a href="/api/homeassistant_garmin/builder">Back to builder</a></p>
    <h2 id="number-picker">Number picker example</h2>
    <p>For a normal light dimmer, choose a light such as <code>light.living_room</code>, set Behavior to <strong>Number picker</strong>, and leave the override fields blank.</p>
    <p>The builder generates <code>light.turn_on</code> with brightness defaults: read attribute <code>brightness</code>, set data attribute <code>brightness</code>, minimum <code>0</code>, maximum <code>255</code>, and step <code>5</code>.</p>
    <p>The fields under Number picker are overrides. Use them only when the generated defaults are wrong or when configuring a custom number helper.</p>
    <p>Transition seconds is experimental for numeric picker items. Some GarminHomeAssistant versions do not pass extra action data from numeric picker calls.</p>
    <p><a href="#top">Back to top</a> | <a href="/api/homeassistant_garmin/builder">Back to builder</a></p>
    <h2 id="basics">Builder basics</h2>
    <ul>
      <li>Use <strong>Add Item</strong> for lights, switches, sensors, scripts, scenes, automations, and numeric controls.</li>
      <li>Use <strong>Add Submenu</strong> to group items by room or purpose.</li>
      <li>Leave behavior on <strong>Automatic</strong> unless you need a specific type.</li>
      <li>Use optional safety settings only for confirmation, PIN, disabled seasonal items, or exit-after-action behavior.</li>
      <li>The JSON editor is an advanced escape hatch. Most users should use the forms.</li>
    </ul>
    <p><a href="#top">Back to top</a> | <a href="/api/homeassistant_garmin/builder">Back to builder</a></p>
    <h2 id="troubleshooting">Troubleshooting</h2>
    <ul>
      <li>If the watch cannot connect, verify the API URL ends in <code>/api</code> and uses a URL reachable from your phone.</li>
      <li>If the menu is missing, confirm you saved the dashboard and copied the current Configuration URL.</li>
      <li>If an action fails, test the same service in Home Assistant Developer Tools first.</li>
      <li>If a number picker does nothing, start with a supported light and blank override fields.</li>
      <li>If external links refuse to connect, the site likely blocked Home Assistant's embedded frame. Use the copy fallback and open it in your browser.</li>
      <li>Some emojis may not render on every Garmin device, especially in glance text.</li>
    </ul>
    <p><a href="#top">Back to top</a> | <a href="/api/homeassistant_garmin/builder">Back to builder</a></p>
  </main>
</body>
</html>"""


def _builder_html(dashboard: dict, base_url: str) -> str:
    """Build the first dashboard-builder page."""
    setup_code = escape(str(dashboard["setup_code"]))
    configured_base_url = str(dashboard.get("base_url") or base_url).rstrip("/")
    display_dashboard = dict(dashboard)
    display_dashboard["base_url"] = configured_base_url
    escaped_base_url = escape(configured_base_url)
    api_url = escape(f"{configured_base_url}/api")
    config_url = escape(
        f"{configured_base_url}/api/homeassistant_garmin/garminhomeassistant/config/{setup_code}"
    )
    dashboard_json = json_dumps(display_dashboard).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GarminHomeAssistant Companion Builder</title>
  <style>
    body {{
      background: #111;
      color: #f5f5f5;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
      margin: 0;
      padding: 20px;
    }}
    main {{
      margin: 0 auto;
      max-width: 980px;
    }}
    h1 {{
      font-size: 1.6rem;
      margin: 0 0 .4rem;
    }}
    h2 {{
      font-size: 1.1rem;
      margin-top: 1.6rem;
    }}
    .panel {{
      background: #161616;
      border: 1px solid #2a2a2a;
      border-radius: 8px;
      margin-top: 1rem;
      padding: 1rem;
    }}
    .panel h2 {{
      margin-top: 0;
    }}
    details.panel > summary {{
      cursor: pointer;
      font-size: 1.08rem;
      font-weight: 700;
      list-style-position: inside;
    }}
    details.panel > summary + * {{
      margin-top: .8rem;
    }}
    label {{
      color: #b8c0cc;
      display: block;
      font-size: .86rem;
      margin: 1rem 0 .35rem;
    }}
    input, textarea, select {{
      background: #1e1e1e;
      border: 1px solid #555;
      border-radius: 6px;
      box-sizing: border-box;
      color: #fff;
      font: inherit;
      padding: .7rem;
      width: 100%;
    }}
    textarea {{
      display: none;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
      min-height: 430px;
      white-space: pre;
    }}
    button, a.button {{
      background: #03a9f4;
      border: 0;
      border-radius: 6px;
      color: #00151f;
      cursor: pointer;
      display: inline-block;
      font-weight: 700;
      margin: .8rem .5rem .2rem 0;
      padding: .7rem 1rem;
      text-decoration: none;
      touch-action: manipulation;
    }}
    .secondary {{
      background: #333;
      color: #fff;
    }}
    .insert-button,
    .emoji-toggle {{
      background: #00c853;
      color: #001b0a;
    }}
    .note {{
      background: #20242b;
      border-left: 4px solid #03a9f4;
      margin-top: 1rem;
      padding: .8rem;
    }}
    .grid {{
      display: grid;
      gap: .8rem;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }}
    .copy-row {{
      display: grid;
      gap: .45rem;
      grid-template-columns: 1fr auto;
    }}
    .copy-button {{
      margin: 0;
      min-width: 46px;
      padding: .7rem;
    }}
    .primary-button {{
      background: #03a9f4;
      color: #00151f;
    }}
    .item-list {{
      border: 1px solid #333;
      border-radius: 6px;
      margin-top: .8rem;
      padding: .5rem;
    }}
    .item-row {{
      align-items: center;
      background: #181818;
      border: 1px solid #2a2a2a;
      border-left: 4px solid #4b5563;
      border-radius: 6px;
      display: grid;
      gap: .5rem;
      grid-template-columns: minmax(0, 1fr) auto;
      margin-bottom: .45rem;
      padding: .55rem;
    }}
    .item-row.group-row {{
      background: #18222b;
      border-left-color: #03a9f4;
    }}
    .item-row.leaf-row {{
      border-left-color: #6b7280;
    }}
    .item-badge {{
      border-radius: 999px;
      display: inline-block;
      font-size: .72rem;
      font-weight: 700;
      margin-right: .4rem;
      padding: .12rem .45rem;
      text-transform: uppercase;
    }}
    .group-badge {{
      background: #073a52;
      color: #9ee7ff;
    }}
    .item-type-badge {{
      background: #2d3239;
      color: #d6dde8;
    }}
    .item-meta {{
      color: #aeb7c2;
      font-size: .85rem;
      grid-column: 2;
    }}
    .item-label {{
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      column-gap: .35rem;
      min-width: 0;
    }}
    .item-main {{
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      column-gap: .35rem;
      min-width: 0;
    }}
    .item-title {{
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      line-height: 1.25;
    }}
    .item-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: .35rem;
      justify-content: flex-end;
    }}
    .icon-button {{
      background: #03a9f4;
      color: #00151f;
      margin: 0;
      min-width: 0;
      padding: .45rem .6rem;
    }}
    .action-up {{
      width: 3.5rem;
    }}
    .action-down {{
      width: 4.35rem;
    }}
    .action-edit {{
      width: 3.9rem;
    }}
    .action-remove {{
      width: 5.6rem;
    }}
    .danger {{
      background: #03a9f4;
      color: #00151f;
    }}
    .status {{
      color: #9ee493;
      min-height: 1.4rem;
    }}
    .status.error {{
      background: #321818;
      border-left: 4px solid #ff5252;
      color: #ffd2d2;
      padding: .65rem;
    }}
    .companion-note a {{
      color: #8bdcff;
    }}
    .top-links {{
      display: flex;
      flex-wrap: wrap;
      gap: .6rem;
      margin-top: .8rem;
    }}
    .mini-link {{
      align-items: center;
      appearance: none;
      background: #262626;
      border: 0;
      border-radius: 999px;
      box-sizing: border-box;
      color: #d8e8f2;
      cursor: pointer;
      display: inline-flex;
      flex: 0 1 auto;
      font-size: .9rem;
      font-weight: 700;
      height: 2.75rem;
      justify-content: center;
      line-height: 1.2;
      margin: 0;
      min-width: 11.5rem;
      padding: 0 .9rem;
      text-align: center;
      text-decoration: none;
      vertical-align: middle;
    }}
    .copy-panel {{
      background: #14202a;
      border: 1px solid #03a9f4;
      border-radius: 8px;
      box-shadow: 0 10px 28px rgba(0,0,0,.35);
      margin-top: .8rem;
      padding: .8rem;
      position: sticky;
      top: .5rem;
      z-index: 20;
    }}
    .copy-panel[hidden] {{
      display: none;
    }}
    .copy-panel-header {{
      align-items: center;
      display: flex;
      gap: .6rem;
      justify-content: space-between;
      margin-bottom: .5rem;
    }}
    .copy-panel-title {{
      font-weight: 700;
    }}
    .copy-panel textarea {{
      display: block;
      min-height: 4.5rem;
      resize: vertical;
    }}
    .copy-panel button {{
      margin: 0;
    }}
    .copy-panel-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: .5rem;
      margin-top: .6rem;
    }}
    .unsaved-bar {{
      align-items: center;
      background: #14202a;
      border: 1px solid #03a9f4;
      border-radius: 10px 10px 0 0;
      bottom: 0;
      box-shadow: 0 -10px 28px rgba(0,0,0,.35);
      box-sizing: border-box;
      display: none;
      gap: .75rem;
      justify-content: space-between;
      left: 50%;
      max-width: 980px;
      padding: .75rem;
      position: fixed;
      transform: translateX(-50%);
      width: calc(100% - 2rem);
      z-index: 30;
    }}
    .unsaved-bar.visible {{
      display: flex;
    }}
    .stale-bar {{
      align-items: center;
      background: #2a2314;
      border: 1px solid #ffb74d;
      border-radius: 10px 10px 0 0;
      bottom: 0;
      box-shadow: 0 -10px 28px rgba(0,0,0,.35);
      box-sizing: border-box;
      display: none;
      gap: .75rem;
      justify-content: space-between;
      left: 50%;
      max-width: 980px;
      padding: .75rem;
      position: fixed;
      transform: translateX(-50%);
      width: calc(100% - 2rem);
      z-index: 29;
    }}
    .stale-bar.visible {{
      display: flex;
    }}
    .unsaved-copy {{
      min-width: 0;
    }}
    .unsaved-title {{
      font-weight: 800;
    }}
    .unsaved-detail {{
      color: #b9c5d0;
      font-size: .86rem;
    }}
    .unsaved-actions {{
      display: flex;
      flex: 0 0 auto;
      flex-wrap: wrap;
      gap: .5rem;
      justify-content: flex-end;
    }}
    .unsaved-actions button {{
      margin: 0;
    }}
    .action-row {{
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      gap: .6rem;
      margin-top: .8rem;
    }}
    .action-row button {{
      margin: 0;
    }}
    .inline-status {{
      color: #9ee493;
      font-size: .9rem;
      min-height: 1.2rem;
    }}
    .inline-status.error {{
      color: #ffd2d2;
    }}
    .help {{
      color: #aeb7c2;
      font-size: .84rem;
      margin-top: .35rem;
    }}
    .required-label::after {{
      color: #ffb74d;
      content: " *";
      font-weight: 700;
    }}
    .field-legend {{
      color: #b9c5d0;
      font-size: .86rem;
      margin: .75rem 0 0;
      padding-left: 1.2rem;
    }}
    .field-legend li {{
      margin: .25rem 0;
    }}
    .behavior-note {{
      background: #20242b;
      border-left: 4px solid #00c853;
      color: #d9f5e1;
      margin-top: .8rem;
      padding: .7rem;
    }}
    .behavior-config {{
      margin-top: 1rem;
    }}
    .behavior-config .behavior-note {{
      margin-top: 0;
    }}
    .advanced-section {{
      border-top: 1px solid #2a2a2a;
      margin-top: 1rem;
      padding-top: .8rem;
    }}
    .advanced-section[hidden] {{
      display: none;
    }}
    .checkbox-row {{
      align-items: center;
      display: flex;
      gap: .5rem;
      margin-top: .8rem;
    }}
    .checkbox-row input {{
      width: auto;
    }}
    .json-highlight {{
      background: #1e1e1e;
      border: 1px solid #3c3c3c;
      border-radius: 6px;
      color: #d4d4d4;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
      line-height: 1.45;
      margin-top: .8rem;
      max-height: 430px;
      overflow: auto;
      padding: .8rem;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .json-highlight:focus {{
      border-color: #007acc;
      outline: 0;
    }}
    .json-key {{
      color: #9cdcfe;
    }}
    .json-string {{
      color: #ce9178;
    }}
    .json-number {{
      color: #b5cea8;
    }}
    .json-boolean {{
      color: #569cd6;
    }}
    .json-null {{
      color: #569cd6;
    }}
    .tree-prefix {{
      color: #6e7681;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
      line-height: 1.25;
      white-space: pre;
    }}
    .emoji-row {{
      display: flex;
      flex-wrap: wrap;
      gap: .35rem;
      margin-top: .45rem;
    }}
    .emoji-picker {{
      margin-top: .45rem;
      position: relative;
    }}
    .emoji-toggle {{
      cursor: pointer;
      font-size: .86rem;
      font-weight: 700;
      margin: 0;
      padding: .45rem .7rem;
    }}
    .emoji-grid {{
      background: #202020;
      border: 1px solid #404040;
      border-radius: 6px;
      box-shadow: 0 8px 22px rgba(0,0,0,.35);
      box-sizing: border-box;
      display: grid;
      gap: .35rem;
      grid-template-columns: repeat(auto-fill, minmax(2.4rem, 1fr));
      max-height: 280px;
      overflow: auto;
      overscroll-behavior: contain;
      padding: .45rem;
      touch-action: pan-y;
    }}
    .emoji-panel {{
      background: #202020;
      border: 1px solid #404040;
      border-radius: 8px;
      box-shadow: 0 8px 22px rgba(0,0,0,.35);
      box-sizing: border-box;
      margin-top: .45rem;
      max-width: 430px;
      padding: .5rem;
      position: absolute;
      width: min(430px, 92vw);
      z-index: 10;
    }}
    .emoji-search {{
      background: #181818;
      border: 1px solid #404040;
      border-radius: 6px;
      color: #fff;
      display: block;
      margin: 0 0 .45rem;
      padding: .55rem .65rem;
      width: 100%;
    }}
    .emoji-tabs {{
      display: flex;
      gap: .3rem;
      margin-bottom: .45rem;
      overflow-x: auto;
      padding-bottom: .1rem;
    }}
    .emoji-tab {{
      background: #2a2a2a;
      color: #e8eef4;
      flex: 0 0 auto;
      font-size: .78rem;
      margin: 0;
      padding: .38rem .55rem;
    }}
    .emoji-tab.active {{
      background: #03a9f4;
      color: #00151f;
    }}
    .emoji-picker:not(.open) .emoji-panel {{
      display: none;
    }}
    .emoji-button {{
      background: #262626;
      color: #fff;
      margin: 0;
      min-width: 2.2rem;
      padding: .4rem;
    }}
    .template-wrap {{
      position: relative;
    }}
    .template-tools {{
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      gap: .5rem;
      margin-top: .45rem;
    }}
    .template-suggestions,
    .entity-suggestions {{
      background: #202020;
      border: 1px solid #404040;
      border-radius: 6px;
      box-shadow: 0 8px 22px rgba(0,0,0,.35);
      box-sizing: border-box;
      display: none;
      left: 0;
      max-height: 240px;
      opacity: 1;
      overflow: auto;
      position: absolute;
      right: 0;
      top: calc(100% + .25rem);
      z-index: 10;
    }}
    .entity-suggestions {{
      max-height: 420px;
      right: auto;
      width: min(560px, calc(100vw - 2rem));
    }}
    .template-suggestion,
    .entity-suggestion {{
      background: #202020;
      border: 0;
      border-bottom: 1px solid #2e2e2e;
      border-radius: 0;
      color: #f5f5f5;
      display: block;
      font-weight: 500;
      margin: 0;
      padding: .55rem .7rem;
      text-align: left;
      width: 100%;
    }}
    .entity-suggestion {{
      align-items: center;
      display: grid;
      gap: .65rem;
      grid-template-columns: 2rem minmax(0, 1fr) auto;
      min-height: 4rem;
    }}
    .entity-icon {{
      color: #b8c0cc;
      font-size: 1.35rem;
      text-align: center;
    }}
    .entity-name {{
      color: #f5f5f5;
      font-weight: 700;
      line-height: 1.2;
    }}
    .entity-sub {{
      color: #aeb7c2;
      font-size: .82rem;
      line-height: 1.25;
      margin-top: .15rem;
      overflow-wrap: anywhere;
    }}
    .entity-domain {{
      color: #aeb7c2;
      font-size: .82rem;
      white-space: nowrap;
    }}
    .template-suggestion small,
    .entity-suggestion small {{
      color: #aeb7c2;
      display: block;
      font-size: .76rem;
      margin-top: .12rem;
    }}
    .template-suggestion.active,
    .entity-suggestion.active {{
      background: #123b52;
    }}
    .watch-preview {{
      background: #000;
      border: 1px solid #22433e;
      border-radius: 8px;
      margin-top: .8rem;
      max-width: 320px;
      padding: .8rem;
    }}
    .watch-row {{
      align-items: center;
      border-bottom: 1px solid #12312d;
      display: grid;
      gap: .7rem;
      grid-template-columns: 2rem 1fr;
      min-height: 3.8rem;
    }}
    .watch-type {{
      color: #00bfff;
      font-size: 1.25rem;
      text-align: center;
    }}
    .watch-title {{
      color: #f5f5f5;
      font-size: 1.05rem;
      line-height: 1.2;
    }}
    .watch-subtitle {{
      color: #d8d8d8;
      font-size: .85rem;
      line-height: 1.2;
      margin-top: .25rem;
    }}
    .watch-subtitle[hidden] {{
      display: none;
    }}
    @media (max-width: 640px) {{
      .item-row {{
        align-items: stretch;
        grid-template-columns: 1fr;
      }}
      .item-actions {{
        justify-content: flex-start;
      }}
      .item-actions .icon-button {{
        text-align: center;
      }}
      .unsaved-bar {{
        align-items: stretch;
        border-radius: 0;
        flex-direction: column;
        left: 0;
        transform: none;
        width: 100%;
      }}
      .stale-bar {{
        align-items: stretch;
        border-radius: 0;
        flex-direction: column;
        left: 0;
        transform: none;
        width: 100%;
      }}
      .unsaved-actions {{
        justify-content: stretch;
      }}
      .unsaved-actions button {{
        flex: 1 1 auto;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>GarminHomeAssistant Companion Builder</h1>
    <p>Build the GarminHomeAssistant menu from Home Assistant, then copy the setup values into the Connect IQ app settings.</p>
    <div class="note companion-note">
      This Home Assistant integration is a companion builder for the
      <a href="https://apps.garmin.com/en-US/apps/61c91d28-ec5e-438d-9f83-39e9f45b199d">GarminHomeAssistant Connect IQ application</a>
      by house-of-abbey. It generates the configuration URL and JSON menu that app expects.
    </div>
    <div class="top-links">
      <a class="mini-link" href="/api/homeassistant_garmin/docs/getting-started">Open Getting Started</a>
      <a class="mini-link" href="/api/homeassistant_garmin/docs/getting-started#troubleshooting">Open Troubleshooting</a>
      <button class="mini-link" data-open-url="https://apps.garmin.com/en-US/apps/61c91d28-ec5e-438d-9f83-39e9f45b199d">Open app listing</button>
      <button class="mini-link" data-open-url="https://github.com/house-of-abbey/GarminHomeAssistant">Open app docs</button>
    </div>
    <div class="copy-panel" id="copy-panel" hidden>
      <div class="copy-panel-header">
        <div>
          <div class="copy-panel-title" id="copy-panel-title">Copy value</div>
          <div class="help" id="copy-panel-help">The value is selected. Press Ctrl+C if it did not copy automatically.</div>
        </div>
        <button class="secondary" id="copy-panel-close" type="button">Close</button>
      </div>
      <textarea id="copy-panel-value" readonly></textarea>
      <div class="copy-panel-actions">
        <button id="copy-panel-copy" type="button">Copy</button>
      </div>
    </div>
    <details class="panel">
      <summary>Quick start help</summary>
      <p>GarminHomeAssistant needs a secure URL that the Garmin Connect phone app can reach.</p>
      <ul>
        <li><strong>Nabu Casa / Home Assistant Cloud</strong> is the easiest paid option and is usually the friendliest setup.</li>
        <li><strong>Your own HTTPS reverse proxy</strong> can also work if it has a publicly trusted certificate.</li>
        <li><strong>Cloudflare Tunnel or similar</strong> can work when configured with the headers/settings GarminHomeAssistant expects.</li>
      </ul>
      <p>The builder tries to use your Nabu Casa URL when available, but it is not required. Use whatever external HTTPS URL works reliably from your phone/watch path.</p>
      <p>Setup flow: install GarminHomeAssistant, copy the API URL, copy the Configuration URL, paste your Home Assistant long-lived token into GarminHomeAssistant, then save this dashboard.</p>
    </details>

    <details class="panel">
      <summary>Watch App Settings</summary>
      <div class="note">
        Create a Home Assistant long-lived access token from your user profile and paste it into GarminHomeAssistant's API key setting.
      </div>
      <label>Base URL</label>
      <div class="copy-row">
        <input id="base-url" value="{escaped_base_url}" onclick="this.select()">
        <button class="copy-button" data-copy="base-url" title="Copy Base URL">Copy</button>
        <button class="copy-button" id="update-base-url" title="Update JSON">Update JSON</button>
      </div>
      <label>API URL</label>
      <div class="copy-row">
        <input id="api-url" readonly value="{api_url}" onclick="this.select()">
        <button class="copy-button" data-copy="api-url" title="Copy API URL">Copy</button>
      </div>
      <label>Configuration URL</label>
      <div class="copy-row">
        <input id="config-url" readonly value="{config_url}" onclick="this.select()">
        <button class="copy-button" data-copy="config-url" title="Copy Configuration URL">Copy</button>
      </div>
      <div>
        <button class="secondary" id="rotate-code">Rotate configuration key</button>
      </div>

      <div class="note">
        The URLs should use your Home Assistant Cloud / Nabu Casa URL when available.
        If the URLs are wrong, update the Base URL here, save, then copy the generated URLs.
      </div>
    </details>

    <section class="panel">
      <h2>Glance</h2>
      <div class="grid">
        <div>
          <label for="glance-type">Glance behavior</label>
          <select id="glance-type">
            <option value="status">Show API status</option>
            <option value="info">Show custom text</option>
          </select>
        </div>
        <div id="glance-template-field">
          <label for="glance-content">Glance text template</label>
          <div class="template-wrap">
            <input id="glance-content" placeholder="Solar Battery: {{ states('sensor.example') }}%" autocomplete="off">
            <div class="template-suggestions" id="glance-template-suggestions"></div>
          </div>
          <div class="template-tools">
            <div class="emoji-picker">
              <button type="button" class="emoji-toggle">Insert Emoji</button>
              <div class="emoji-grid" data-target="glance-content"></div>
            </div>
          </div>
        </div>
      </div>
      <div class="action-row">
        <button id="update-glance">Update and save glance</button>
        <span class="inline-status" id="glance-status"></span>
      </div>
    </section>

    <section class="panel" id="item-panel">
    <h2 id="item-section-title">Add Item</h2>
    <div class="grid">
      <div>
        <label class="required-label" for="entity-picker">Entity</label>
        <div class="template-wrap">
          <input id="entity-picker" placeholder="light.living_room" autocomplete="off">
          <div class="entity-suggestions" id="entity-suggestions"></div>
        </div>
        <datalist id="entities"></datalist>
      </div>
      <div>
        <label class="required-label" for="item-name">Name on watch</label>
        <input id="item-name" placeholder="Living Room">
        <div class="emoji-picker">
          <button type="button" class="emoji-toggle">Insert Emoji</button>
          <div class="emoji-grid" data-target="item-name"></div>
        </div>
      </div>
      <div>
        <label class="required-label" for="item-type">Behavior</label>
        <select id="item-type">
          <option value="auto">Automatic</option>
          <option value="toggle">Toggle</option>
          <option value="tap">Run action</option>
          <option value="info">Info only</option>
          <option value="numeric">Number picker</option>
        </select>
      </div>
      <div>
        <label for="parent-group">Parent submenu</label>
        <select id="parent-group">
          <option value="">Top level</option>
        </select>
      </div>
    </div>
    <div class="behavior-config">
      <div class="behavior-note" id="item-behavior-help"></div>
      <div class="advanced-section" id="custom-action-options">
        <h3>Run action setup</h3>
        <div class="grid">
          <div>
            <label for="item-action">Custom action</label>
            <input id="item-action" placeholder="Optional, e.g. light.turn_on">
          </div>
          <div>
            <label for="item-data">Custom action data JSON</label>
            <input id="item-data" placeholder='{{"brightness": 128}}'>
          </div>
        </div>
        <ul class="field-legend">
          <li>Select an entity for scripts, scenes, automations, buttons, or entity-specific services.</li>
          <li>Use Custom action only when you need to override the action GarminHomeAssistant would infer.</li>
          <li>Custom action data must be a JSON object, such as <code>{{"entity_id":"light.living_room","brightness":128}}</code>.</li>
        </ul>
      </div>
      <div class="advanced-section" id="numeric-picker-options">
        <h3>Number picker setup</h3>
        <div class="grid">
          <div>
            <label for="numeric-min">Override minimum</label>
            <input id="numeric-min" type="number" step="any" placeholder="0">
          </div>
          <div>
            <label for="numeric-max">Override maximum</label>
            <input id="numeric-max" type="number" step="any" placeholder="100">
          </div>
          <div>
            <label for="numeric-step">Override step</label>
            <input id="numeric-step" type="number" step="any" placeholder="1">
          </div>
          <div>
            <label for="numeric-attribute">Read attribute</label>
            <input id="numeric-attribute" placeholder="Optional, e.g. brightness">
          </div>
          <div>
            <label for="numeric-data-attribute">Override set data attribute</label>
            <input id="numeric-data-attribute" placeholder="Optional, e.g. value">
          </div>
          <div>
            <label for="numeric-transition">Transition seconds</label>
            <input id="numeric-transition" type="number" step="0.1" min="0" placeholder="Optional, e.g. 2">
          </div>
        </div>
        <ul class="field-legend">
          <li>For a normal light dimmer, choose the light entity, set Behavior to <strong>Number picker</strong>, and leave these override fields blank.</li>
          <li>Example for <code>light.living_room</code>: generated defaults are action <code>light.turn_on</code>, read attribute <code>brightness</code>, set data attribute <code>brightness</code>, minimum <code>0</code>, maximum <code>255</code>, step <code>5</code>.</li>
          <li>Only fill these fields when you need to override the generated defaults for brightness, volume, fan percentage, cover position, valve position, thermostat temperature, or an input_number helper.</li>
          <li>Transition seconds is experimental for numeric items because GarminHomeAssistant may ignore extra action data on numeric picker calls.</li>
          <li>For an <code>input_number</code> or <code>number</code> helper, common overrides are minimum <code>0</code>, maximum <code>100</code>, step <code>1</code>, blank read attribute, and set data attribute <code>value</code>.</li>
        </ul>
      </div>
    </div>
    <label for="item-content">Secondary text template</label>
    <div class="template-wrap">
      <input id="item-content" placeholder="{{ states('sensor.example') }}" autocomplete="off">
      <div class="template-suggestions" id="item-template-suggestions"></div>
    </div>
    <div class="template-tools">
      <button class="insert-button" id="insert-item-state">Insert selected entity state</button>
      <div class="emoji-picker">
        <button type="button" class="emoji-toggle">Insert Emoji</button>
        <div class="emoji-grid" data-target="item-content"></div>
      </div>
      <span class="item-meta" id="item-template-result" style="display:none"></span>
    </div>
    <div class="watch-preview">
      <div class="watch-row">
        <div class="watch-type" id="watch-preview-icon">i</div>
        <div>
          <div class="watch-title" id="watch-preview-title">Item preview</div>
          <div class="watch-subtitle" id="watch-preview-subtitle">Secondary text preview</div>
        </div>
      </div>
    </div>
    <details class="panel">
      <summary>Optional GarminHomeAssistant safety and visibility options</summary>
      <p class="help">Leave these alone for normal lights, switches, sensors, scenes, scripts, automations, and number pickers. Use them only when this watch item needs extra confirmation, PIN protection, seasonal hiding, or should exit the app after running.</p>
      <div class="advanced-section" id="security-options">
      <h3>Safety and visibility</h3>
      <div class="grid">
        <div class="checkbox-row">
          <input id="item-enabled" type="checkbox" checked>
          <label for="item-enabled">Show this item</label>
        </div>
        <div class="checkbox-row">
          <input id="item-pin" type="checkbox">
          <label for="item-pin">Require GarminHomeAssistant PIN</label>
        </div>
        <div class="checkbox-row">
          <input id="item-exit" type="checkbox">
          <label for="item-exit">Exit app after action</label>
        </div>
        <div class="checkbox-row">
          <input id="item-confirm-enabled" type="checkbox">
          <label for="item-confirm-enabled">Ask for confirmation</label>
        </div>
      </div>
      <label for="item-confirm-message">Confirmation message</label>
      <input id="item-confirm-message" placeholder="Optional custom message">
      <div class="help">Optional text shown before the watch runs this action. Leave blank to use GarminHomeAssistant's default confirmation text.</div>
      </div>
    </details>
    <div class="action-row">
      <button id="add-item">Add item</button>
      <button class="secondary" id="cancel-edit-item" style="display:none">Cancel edit</button>
      <span class="inline-status" id="item-status"></span>
    </div>
    </section>

    <section class="panel" id="group-panel">
    <h2 id="group-section-title">Add Submenu</h2>
    <div class="grid">
      <div>
        <label for="group-name">Submenu name</label>
        <input id="group-name" placeholder="Living Room">
        <div class="emoji-picker">
          <button type="button" class="emoji-toggle">Insert Emoji</button>
          <div class="emoji-grid" data-target="group-name"></div>
        </div>
      </div>
      <div>
        <label for="group-parent">Parent submenu</label>
        <select id="group-parent">
          <option value="">Top level</option>
        </select>
      </div>
    </div>
    <label for="group-content">Submenu secondary text template</label>
    <div class="template-wrap">
      <input id="group-content" placeholder="Optional status text shown under the submenu" autocomplete="off">
      <div class="template-suggestions" id="group-template-suggestions"></div>
    </div>
    <div class="template-tools">
      <div class="emoji-picker">
        <button type="button" class="emoji-toggle">Insert Emoji</button>
        <div class="emoji-grid" data-target="group-content"></div>
      </div>
      <span class="item-meta" id="group-template-result" style="display:none"></span>
    </div>
    <details class="panel">
      <summary>Advanced submenu options</summary>
      <label for="group-title">Submenu screen title</label>
      <input id="group-title" placeholder="Optional title shown inside submenu">
      <div class="help">The menu row can have a short name, while the submenu screen can have a longer title.</div>
      <div class="checkbox-row">
        <input id="group-enabled" type="checkbox" checked>
        <label for="group-enabled">Show this submenu</label>
      </div>
    </details>
    <div class="action-row">
      <button id="add-group">Add submenu</button>
      <button class="secondary" id="cancel-edit-group" style="display:none">Cancel edit</button>
      <span class="inline-status" id="group-status"></span>
    </div>
    </section>

    <section class="panel">
      <h2>Menu Items</h2>
      <div id="item-list" class="item-list"></div>
      <div class="action-row">
        <button id="save">Save dashboard</button>
        <span class="inline-status" id="save-status"></span>
      </div>
    </section>

    <details class="panel">
      <summary>Dashboard JSON</summary>
      <textarea id="dashboard"></textarea>
      <pre id="json-highlight" class="json-highlight" contenteditable="true" spellcheck="false" role="textbox" aria-label="Dashboard JSON editor"></pre>
      <div>
        <button class="secondary" id="format">Format JSON</button>
        <button class="primary-button" id="copy-dashboard-json">Copy dashboard JSON</button>
        <button class="primary-button" id="copy-config-url">Copy Garmin JSON URL</button>
        <button class="secondary" id="view-config-url">View Garmin JSON</button>
        <span class="inline-status" id="json-status"></span>
      </div>
    </details>
    <p class="status" id="status"></p>
    <div class="stale-bar" id="stale-warning" aria-live="polite">
      <div class="unsaved-copy">
        <div class="unsaved-title">Dashboard changed elsewhere</div>
        <div class="unsaved-detail">Reload the latest saved dashboard before making more edits.</div>
      </div>
      <div class="unsaved-actions">
        <button id="reload-dashboard">Reload latest dashboard</button>
      </div>
    </div>
    <div class="unsaved-bar" id="unsaved-bar" aria-live="polite">
      <div class="unsaved-copy">
        <div class="unsaved-title">Unsaved dashboard changes</div>
        <div class="unsaved-detail">Save to publish these changes to GarminHomeAssistant.</div>
      </div>
      <div class="unsaved-actions">
        <button id="unsaved-save">Save dashboard</button>
        <button class="secondary" id="unsaved-reload">Discard changes</button>
      </div>
    </div>
  </main>
  <script>
    const dashboard = document.getElementById('dashboard');
    const jsonHighlight = document.getElementById('json-highlight');
    const statusEl = document.getElementById('status');
    const staleWarning = document.getElementById('stale-warning');
    const unsavedBar = document.getElementById('unsaved-bar');
    const unsavedSave = document.getElementById('unsaved-save');
    const unsavedReload = document.getElementById('unsaved-reload');
    const baseUrlInput = document.getElementById('base-url');
    const apiUrl = document.getElementById('api-url');
    const configUrl = document.getElementById('config-url');
    const copyPanel = document.getElementById('copy-panel');
    const copyPanelTitle = document.getElementById('copy-panel-title');
    const copyPanelHelp = document.getElementById('copy-panel-help');
    const copyPanelValue = document.getElementById('copy-panel-value');
    const copyPanelCopy = document.getElementById('copy-panel-copy');
    const glanceType = document.getElementById('glance-type');
    const glanceContent = document.getElementById('glance-content');
    const glanceTemplateField = document.getElementById('glance-template-field');
    const itemList = document.getElementById('item-list');
    const entityPicker = document.getElementById('entity-picker');
    const entityList = document.getElementById('entities');
    const entitySuggestions = document.getElementById('entity-suggestions');
    const itemName = document.getElementById('item-name');
    const itemType = document.getElementById('item-type');
    const itemContent = document.getElementById('item-content');
    const itemEnabled = document.getElementById('item-enabled');
    const itemPin = document.getElementById('item-pin');
    const itemExit = document.getElementById('item-exit');
    const itemConfirmEnabled = document.getElementById('item-confirm-enabled');
    const itemConfirmMessage = document.getElementById('item-confirm-message');
    const itemAction = document.getElementById('item-action');
    const itemData = document.getElementById('item-data');
    const itemBehaviorHelp = document.getElementById('item-behavior-help');
    const customActionOptions = document.getElementById('custom-action-options');
    const numericPickerOptions = document.getElementById('numeric-picker-options');
    const numericMin = document.getElementById('numeric-min');
    const numericMax = document.getElementById('numeric-max');
    const numericStep = document.getElementById('numeric-step');
    const numericAttribute = document.getElementById('numeric-attribute');
    const numericDataAttribute = document.getElementById('numeric-data-attribute');
    const numericTransition = document.getElementById('numeric-transition');
    const itemTemplateResult = document.getElementById('item-template-result');
    const watchPreviewIcon = document.getElementById('watch-preview-icon');
    const watchPreviewTitle = document.getElementById('watch-preview-title');
    const watchPreviewSubtitle = document.getElementById('watch-preview-subtitle');
    const parentGroup = document.getElementById('parent-group');
    const groupName = document.getElementById('group-name');
    const groupContent = document.getElementById('group-content');
    const groupTitle = document.getElementById('group-title');
    const groupEnabled = document.getElementById('group-enabled');
    const groupTemplateResult = document.getElementById('group-template-result');
    const groupParent = document.getElementById('group-parent');
    const itemTemplateSuggestions = document.getElementById('item-template-suggestions');
    const groupTemplateSuggestions = document.getElementById('group-template-suggestions');
    const glanceTemplateSuggestions = document.getElementById('glance-template-suggestions');
    const itemPanel = document.getElementById('item-panel');
    const groupPanel = document.getElementById('group-panel');
    const itemSectionTitle = document.getElementById('item-section-title');
    const groupSectionTitle = document.getElementById('group-section-title');
    const addItemButton = document.getElementById('add-item');
    const cancelEditItemButton = document.getElementById('cancel-edit-item');
    const addGroupButton = document.getElementById('add-group');
    const cancelEditGroupButton = document.getElementById('cancel-edit-group');
    const localStatusTargets = {{
      glance: document.getElementById('glance-status'),
      item: document.getElementById('item-status'),
      group: document.getElementById('group-status'),
      save: document.getElementById('save-status'),
      json: document.getElementById('json-status'),
    }};
    let entities = [];
    let lastSavedDashboard = null;
    let suppressDirtyState = false;
    const emojiPresets = [
      'ðŸ’¡','ðŸ”¦','ðŸ•¯ï¸','ðŸŒˆ','ðŸŽ›ï¸','ðŸ”˜','â»','âœ…','âŒ','âš ï¸','â„¹ï¸','ðŸ””','ðŸ”•',
      'ðŸ ','ðŸ›ï¸','ðŸ›‹ï¸','ðŸ½ï¸','ðŸš¿','ðŸ§º','ðŸ¢','ðŸšª','ðŸªŸ','ðŸš—','ðŸ“¦','ðŸ“¬',
      'ðŸŒ¡ï¸','â„ï¸','ðŸ”¥','ðŸ’§','ðŸ’¦','â˜€ï¸','ðŸŒ™','ðŸŒ§ï¸','â˜”','ðŸŒ¬ï¸','ðŸ’¨','ðŸŒ¿','ðŸŒ±',
      'ðŸ”’','ðŸ”“','ðŸ”‘','ðŸ›¡ï¸','ðŸš¨','ðŸ‘€','ðŸƒ','ðŸ§','ðŸ‘¤','ðŸ‘¥',
      'ðŸ”‹','ðŸª«','âš¡','ðŸ”Œ','ðŸ“ˆ','ðŸ“‰','ðŸ“Š','â±ï¸','â°','ðŸ•’',
      'ðŸŽ¬','ðŸŽ®','ðŸŽµ','ðŸ“º','ðŸ”Š','ðŸ”‡','ðŸ“¶','ðŸ›œ','ðŸ–¥ï¸','ðŸ–¨ï¸',
      'ðŸ§Š','ðŸ§¯','ðŸ§¹','ðŸ§½','ðŸ—‘ï¸','ðŸ§¼','ðŸª´','ðŸƒ','ðŸŒŠ','ðŸ§°','ðŸ”§','ðŸª›'
    ];
    const emojiCatalog = [
      ['\\uD83D\\uDCA1', 'light bulb lamp brightness idea'],
      ['\\uD83D\\uDD26', 'flashlight light torch'],
      ['\\uD83D\\uDD6F\\uFE0F', 'candle dim warm light'],
      ['\\uD83C\\uDF08', 'rainbow color rgb light'],
      ['\\uD83C\\uDF9B\\uFE0F', 'sliders controls settings'],
      ['\\uD83D\\uDD18', 'button switch toggle'],
      ['\\u23FB', 'power on off'],
      ['\\u2705', 'check ok yes active on'],
      ['\\u274C', 'x no off closed inactive'],
      ['\\u26A0\\uFE0F', 'warning alert problem'],
      ['\\u2139\\uFE0F', 'info information status'],
      ['\\uD83D\\uDD14', 'bell notification alert'],
      ['\\uD83D\\uDD15', 'mute notification off'],
      ['\\uD83C\\uDFE0', 'home house'],
      ['\\uD83D\\uDECF\\uFE0F', 'bed bedroom sleep'],
      ['\\uD83D\\uDECB\\uFE0F', 'couch living room lounge'],
      ['\\uD83C\\uDF7D\\uFE0F', 'kitchen dining food'],
      ['\\uD83D\\uDEBF', 'shower bathroom water'],
      ['\\uD83E\\uDDFA', 'laundry basket washer dryer'],
      ['\\uD83C\\uDFE2', 'office building work'],
      ['\\uD83D\\uDEAA', 'door entry open closed'],
      ['\\uD83E\\uDE9F', 'window open closed'],
      ['\\uD83D\\uDE97', 'car garage vehicle'],
      ['\\uD83D\\uDCE6', 'package delivery'],
      ['\\uD83D\\uDCEC', 'mail mailbox'],
      ['\\uD83C\\uDF21\\uFE0F', 'temperature thermostat climate'],
      ['\\u2744\\uFE0F', 'cold ac cooling snow'],
      ['\\uD83D\\uDD25', 'heat fire heating'],
      ['\\uD83D\\uDCA7', 'water drop leak humidity'],
      ['\\uD83D\\uDCA6', 'water droplets moisture'],
      ['\\u2600\\uFE0F', 'sun sunny solar day'],
      ['\\uD83C\\uDF19', 'moon night sleep'],
      ['\\uD83C\\uDF27\\uFE0F', 'rain weather'],
      ['\\u2614', 'umbrella rain'],
      ['\\uD83C\\uDF2C\\uFE0F', 'wind air breeze'],
      ['\\uD83D\\uDCA8', 'air fan motion'],
      ['\\uD83C\\uDF3F', 'leaf plant garden eco'],
      ['\\uD83C\\uDF31', 'seedling plant grow'],
      ['\\uD83D\\uDD12', 'lock secure locked'],
      ['\\uD83D\\uDD13', 'unlock unlocked'],
      ['\\uD83D\\uDD11', 'key access'],
      ['\\uD83D\\uDEE1\\uFE0F', 'shield security alarm'],
      ['\\uD83D\\uDEA8', 'siren alarm emergency'],
      ['\\uD83D\\uDC40', 'eyes watch monitor presence'],
      ['\\uD83C\\uDFC3', 'motion running occupancy'],
      ['\\uD83E\\uDDCD', 'person presence home'],
      ['\\uD83D\\uDC64', 'person user'],
      ['\\uD83D\\uDC65', 'people family group'],
      ['\\uD83D\\uDD0B', 'battery power charge'],
      ['\\u26A1', 'energy electricity power'],
      ['\\uD83D\\uDD0C', 'plug outlet power'],
      ['\\uD83D\\uDCC8', 'chart up usage high'],
      ['\\uD83D\\uDCC9', 'chart down usage low'],
      ['\\uD83D\\uDCCA', 'chart stats sensor'],
      ['\\u23F1\\uFE0F', 'timer duration'],
      ['\\u23F0', 'alarm clock schedule'],
      ['\\uD83D\\uDD52', 'clock time'],
      ['\\uD83C\\uDFAC', 'movie media scene'],
      ['\\uD83C\\uDFAE', 'game entertainment'],
      ['\\uD83C\\uDFB5', 'music audio'],
      ['\\uD83D\\uDCFA', 'tv television media'],
      ['\\uD83D\\uDD0A', 'speaker volume audio'],
      ['\\uD83D\\uDD07', 'mute silent audio off'],
      ['\\uD83D\\uDCF6', 'wifi network signal'],
      ['\\uD83D\\uDDA5\\uFE0F', 'computer server desktop'],
      ['\\uD83D\\uDDA8\\uFE0F', 'printer'],
      ['\\uD83E\\uDDCA', 'ice freezer cold'],
      ['\\uD83E\\uDDEF', 'fire extinguisher safety'],
      ['\\uD83E\\uDDF9', 'clean vacuum'],
      ['\\uD83E\\uDDFD', 'cleaning sponge'],
      ['\\uD83D\\uDDD1\\uFE0F', 'trash garbage'],
      ['\\uD83E\\uDDFC', 'soap cleaning'],
      ['\\uD83E\\uDEB4', 'plant pot garden'],
      ['\\uD83C\\uDF43', 'leaf outdoor'],
      ['\\uD83C\\uDF0A', 'water wave pool'],
      ['\\uD83E\\uDDF0', 'toolbox maintenance'],
      ['\\uD83D\\uDD27', 'wrench repair'],
      ['\\uD83E\\uDE9B', 'screwdriver tool']
    ];
    emojiCatalog.push(
      ['\\uD83D\\uDE00', 'smile happy face'],
      ['\\uD83D\\uDE03', 'grin happy face'],
      ['\\uD83D\\uDE0E', 'cool sunglasses face'],
      ['\\uD83E\\uDD73', 'party celebration'],
      ['\\uD83D\\uDE34', 'sleep tired'],
      ['\\uD83E\\uDD76', 'cold freezing face'],
      ['\\uD83E\\uDD75', 'hot face heat'],
      ['\\uD83D\\uDE31', 'scared alarm face'],
      ['\\uD83D\\uDE21', 'angry problem face'],
      ['\\uD83D\\uDE4C', 'hands success done'],
      ['\\uD83D\\uDC4D', 'thumbs up approve'],
      ['\\uD83D\\uDC4E', 'thumbs down reject'],
      ['\\uD83D\\uDC4F', 'clap applause'],
      ['\\uD83D\\uDC4B', 'wave hello'],
      ['\\uD83D\\uDCAA', 'strong power strength'],
      ['\\uD83D\\uDC96', 'heart love favorite'],
      ['\\uD83D\\uDC99', 'blue heart favorite'],
      ['\\uD83D\\uDC9A', 'green heart favorite'],
      ['\\uD83D\\uDC9B', 'yellow heart favorite'],
      ['\\u2B50', 'star favorite'],
      ['\\uD83D\\uDCA4', 'sleep zzz quiet'],
      ['\\uD83D\\uDCAF', 'hundred perfect'],
      ['\\uD83D\\uDCA3', 'critical danger'],
      ['\\uD83D\\uDD34', 'red circle status'],
      ['\\uD83D\\uDFE0', 'orange circle status'],
      ['\\uD83D\\uDFE1', 'yellow circle status'],
      ['\\uD83D\\uDFE2', 'green circle status'],
      ['\\uD83D\\uDD35', 'blue circle status'],
      ['\\uD83D\\uDFE3', 'purple circle status'],
      ['\\u26AB', 'black circle status'],
      ['\\u26AA', 'white circle status'],
      ['\\u2B06\\uFE0F', 'arrow up increase'],
      ['\\u2B07\\uFE0F', 'arrow down decrease'],
      ['\\u2B05\\uFE0F', 'arrow left previous'],
      ['\\u27A1\\uFE0F', 'arrow right next'],
      ['\\uD83D\\uDD3C', 'up button increase'],
      ['\\uD83D\\uDD3D', 'down button decrease'],
      ['\\u23EE\\uFE0F', 'previous track'],
      ['\\u23ED\\uFE0F', 'next track'],
      ['\\u23EF\\uFE0F', 'play pause media'],
      ['\\u25B6\\uFE0F', 'play media'],
      ['\\u23F8\\uFE0F', 'pause media'],
      ['\\u23F9\\uFE0F', 'stop media'],
      ['\\u23FA\\uFE0F', 'record media'],
      ['\\uD83D\\uDD01', 'repeat loop automation'],
      ['\\uD83D\\uDD00', 'shuffle random'],
      ['\\uD83D\\uDCCD', 'pin location'],
      ['\\uD83D\\uDCC5', 'calendar date schedule'],
      ['\\uD83D\\uDCC6', 'calendar schedule'],
      ['\\uD83D\\uDD16', 'bookmark favorite'],
      ['\\uD83D\\uDCDD', 'note list'],
      ['\\uD83D\\uDCCB', 'clipboard list'],
      ['\\uD83D\\uDCC4', 'document file'],
      ['\\uD83D\\uDD0D', 'search inspect'],
      ['\\u2699\\uFE0F', 'gear settings automation'],
      ['\\uD83D\\uDCF1', 'phone mobile'],
      ['\\u231A', 'watch garmin wearable'],
      ['\\uD83D\\uDCBB', 'laptop computer'],
      ['\\u2328\\uFE0F', 'keyboard input'],
      ['\\uD83D\\uDCF7', 'camera security'],
      ['\\uD83C\\uDFA5', 'video camera security'],
      ['\\uD83D\\uDCF0', 'news alert'],
      ['\\uD83D\\uDE80', 'rocket fast launch'],
      ['\\u2708\\uFE0F', 'airplane travel away'],
      ['\\uD83D\\uDEB2', 'bike bicycle'],
      ['\\uD83D\\uDE8C', 'bus travel'],
      ['\\uD83D\\uDE9A', 'truck delivery'],
      ['\\u26FD', 'fuel gas car'],
      ['\\uD83C\\uDFD6\\uFE0F', 'vacation beach'],
      ['\\uD83C\\uDFD5\\uFE0F', 'camping away'],
      ['\\uD83C\\uDF06', 'city evening'],
      ['\\uD83C\\uDF03', 'night city'],
      ['\\uD83C\\uDF05', 'sunrise morning'],
      ['\\uD83C\\uDF07', 'sunset evening'],
      ['\\uD83C\\uDF24\\uFE0F', 'mostly sunny weather'],
      ['\\u26C5', 'partly cloudy weather'],
      ['\\u2601\\uFE0F', 'cloudy weather'],
      ['\\u26C8\\uFE0F', 'storm thunder weather'],
      ['\\uD83C\\uDF28\\uFE0F', 'snow weather'],
      ['\\uD83C\\uDF2B\\uFE0F', 'fog weather'],
      ['\\uD83C\\uDF2A\\uFE0F', 'tornado weather'],
      ['\\uD83C\\uDF32', 'tree evergreen outdoor'],
      ['\\uD83C\\uDF33', 'tree outdoor'],
      ['\\uD83C\\uDF3C', 'flower garden'],
      ['\\uD83C\\uDF37', 'flower garden spring'],
      ['\\u2615', 'coffee kitchen morning'],
      ['\\uD83C\\uDF7A', 'beer drink'],
      ['\\uD83C\\uDF77', 'wine drink'],
      ['\\uD83E\\uDD64', 'drink cup'],
      ['\\uD83E\\uDFA3', 'bucket cleaning'],
      ['\\uD83E\\uDDFB', 'toilet paper bathroom'],
      ['\\uD83D\\uDEC1', 'bathtub bathroom'],
      ['\\uD83D\\uDEBD', 'toilet bathroom'],
      ['\\uD83D\\uDC55', 'shirt laundry'],
      ['\\uD83E\\uDDE6', 'socks laundry'],
      ['\\uD83E\\uDDF3', 'luggage travel'],
      ['\\uD83D\\uDCB0', 'money cost energy'],
      ['\\uD83D\\uDCB5', 'dollar cost money'],
      ['\\uD83D\\uDCB3', 'card payment']
    );
    emojiCatalog.push(
      ['\\uD83D\\uDE02', 'laugh tears funny lol'],
      ['\\uD83E\\uDD23', 'rolling laughing funny lol'],
      ['\\uD83D\\uDE2D', 'crying tears sad'],
      ['\\uD83D\\uDE22', 'sad cry disappointed'],
      ['\\uD83D\\uDE05', 'sweat nervous laugh'],
      ['\\uD83D\\uDE06', 'laughing grin funny'],
      ['\\uD83D\\uDE09', 'wink playful'],
      ['\\uD83D\\uDE0A', 'smile blush happy'],
      ['\\uD83D\\uDE07', 'angel good innocent'],
      ['\\uD83D\\uDE08', 'devil mischievous evil'],
      ['\\uD83D\\uDE0D', 'heart eyes love'],
      ['\\uD83D\\uDE18', 'kiss heart love'],
      ['\\uD83D\\uDE1C', 'wink tongue silly'],
      ['\\uD83E\\uDD2A', 'zany silly wild'],
      ['\\uD83E\\uDD14', 'thinking question'],
      ['\\uD83E\\uDD28', 'raised eyebrow suspicious'],
      ['\\uD83D\\uDE44', 'eye roll annoyed'],
      ['\\uD83D\\uDE2C', 'grimace awkward'],
      ['\\uD83E\\uDD10', 'zip mouth quiet'],
      ['\\uD83E\\uDD2B', 'shush quiet'],
      ['\\uD83E\\uDD2D', 'hand over mouth oops'],
      ['\\uD83E\\uDD17', 'hug comfort'],
      ['\\uD83E\\uDEE1', 'salute respect'],
      ['\\uD83D\\uDE4F', 'pray thanks please'],
      ['\\uD83D\\uDC80', 'skull dead funny'],
      ['\\uD83E\\uDD21', 'clown silly'],
      ['\\uD83D\\uDC7B', 'ghost spooky'],
      ['\\uD83D\\uDCA9', 'poop bad problem'],
      ['\\uD83D\\uDC4C', 'ok hand perfect'],
      ['\\u270C\\uFE0F', 'peace victory'],
      ['\\uD83E\\uDD1E', 'fingers crossed hope'],
      ['\\uD83E\\uDD1D', 'handshake agreement'],
      ['\\uD83E\\uDEE0', 'heart hands care'],
      ['\\uD83D\\uDC47', 'point down'],
      ['\\uD83D\\uDC46', 'point up'],
      ['\\uD83D\\uDC49', 'point right'],
      ['\\uD83D\\uDC48', 'point left'],
      ['\\u2728', 'sparkles clean magic'],
      ['\\uD83C\\uDF89', 'party popper celebration'],
      ['\\uD83C\\uDF8A', 'confetti celebration'],
      ['\\uD83C\\uDFC6', 'trophy winner'],
      ['\\uD83C\\uDF81', 'gift present'],
      ['\\uD83C\\uDF82', 'birthday cake'],
      ['\\uD83C\\uDF84', 'christmas tree holiday'],
      ['\\uD83C\\uDF83', 'pumpkin halloween'],
      ['\\u2764\\uFE0F', 'red heart love'],
      ['\\uD83E\\uDDE1', 'orange heart love'],
      ['\\uD83D\\uDC9C', 'purple heart love'],
      ['\\uD83E\\uDD0D', 'white heart love'],
      ['\\uD83D\\uDDA4', 'black heart love'],
      ['\\uD83D\\uDC94', 'broken heart'],
      ['\\uD83D\\uDC95', 'two hearts love'],
      ['\\uD83D\\uDC97', 'growing heart'],
      ['\\uD83D\\uDC98', 'heart arrow love'],
      ['\\uD83D\\uDC9E', 'revolving hearts love'],
      ['\\u2757', 'exclamation important'],
      ['\\u2753', 'question help'],
      ['\\u2049\\uFE0F', 'exclamation question'],
      ['\\u203C\\uFE0F', 'double exclamation'],
      ['\\uD83D\\uDD1D', 'top best'],
      ['\\uD83D\\uDD1C', 'soon later'],
      ['\\uD83D\\uDD19', 'back return'],
      ['\\uD83D\\uDD1A', 'end stop'],
      ['\\uD83D\\uDD1B', 'on active'],
      ['\\uD83D\\uDCF2', 'phone arrow message'],
      ['\\uD83D\\uDCAC', 'chat message'],
      ['\\uD83D\\uDCE2', 'announcement loudspeaker'],
      ['\\uD83D\\uDCE3', 'megaphone announcement'],
      ['\\uD83D\\uDCE1', 'satellite signal'],
      ['\\uD83D\\uDD2D', 'telescope view'],
      ['\\uD83E\\uDDED', 'compass direction'],
      ['\\uD83D\\uDDFA\\uFE0F', 'map location'],
      ['\\uD83D\\uDE4A', 'speak no evil quiet'],
      ['\\uD83D\\uDE48', 'see no evil hide'],
      ['\\uD83D\\uDE49', 'hear no evil mute']
    );
    emojiCatalog.push(
      ['\\uD83D\\uDE10', 'neutral face'],
      ['\\uD83D\\uDE11', 'expressionless face'],
      ['\\uD83D\\uDE12', 'unamused annoyed'],
      ['\\uD83D\\uDE13', 'cold sweat nervous'],
      ['\\uD83D\\uDE14', 'pensive sad'],
      ['\\uD83D\\uDE15', 'confused face'],
      ['\\uD83D\\uDE16', 'confounded face'],
      ['\\uD83D\\uDE17', 'kiss face'],
      ['\\uD83D\\uDE19', 'kissing smiling eyes'],
      ['\\uD83D\\uDE1A', 'kissing closed eyes'],
      ['\\uD83D\\uDE1B', 'tongue face'],
      ['\\uD83D\\uDE1D', 'squint tongue silly'],
      ['\\uD83D\\uDE1E', 'disappointed sad'],
      ['\\uD83D\\uDE1F', 'worried face'],
      ['\\uD83D\\uDE20', 'angry face'],
      ['\\uD83D\\uDE23', 'persevere frustrated'],
      ['\\uD83D\\uDE24', 'triumph steam'],
      ['\\uD83D\\uDE25', 'relieved sad sweat'],
      ['\\uD83D\\uDE26', 'frowning open mouth'],
      ['\\uD83D\\uDE27', 'anguished face'],
      ['\\uD83D\\uDE28', 'fearful face'],
      ['\\uD83D\\uDE29', 'weary tired'],
      ['\\uD83D\\uDE2A', 'sleepy tired'],
      ['\\uD83D\\uDE2B', 'tired face'],
      ['\\uD83D\\uDE2E', 'open mouth surprise'],
      ['\\uD83D\\uDE2F', 'hushed surprise'],
      ['\\uD83D\\uDE30', 'anxious sweat'],
      ['\\uD83D\\uDE32', 'astonished surprise'],
      ['\\uD83D\\uDE33', 'flushed embarrassed'],
      ['\\uD83D\\uDE35', 'dizzy face'],
      ['\\uD83D\\uDE36', 'no mouth quiet'],
      ['\\uD83D\\uDE37', 'mask sick'],
      ['\\uD83E\\uDD12', 'thermometer sick fever'],
      ['\\uD83E\\uDD15', 'head bandage hurt'],
      ['\\uD83E\\uDD22', 'nauseated sick'],
      ['\\uD83E\\uDD2E', 'vomit sick'],
      ['\\uD83E\\uDD27', 'sneeze sick'],
      ['\\uD83E\\uDD20', 'cowboy hat'],
      ['\\uD83E\\uDD78', 'disguised face'],
      ['\\uD83E\\uDD79', 'holding back tears'],
      ['\\uD83E\\uDEE2', 'holding tears sad'],
      ['\\uD83E\\uDEE3', 'peeking face'],
      ['\\uD83E\\uDEE4', 'saluting face'],
      ['\\uD83E\\uDEE8', 'shaking face'],
      ['\\uD83D\\uDC36', 'dog pet'],
      ['\\uD83D\\uDC31', 'cat pet'],
      ['\\uD83D\\uDC2D', 'mouse animal'],
      ['\\uD83D\\uDC39', 'hamster pet'],
      ['\\uD83D\\uDC30', 'rabbit pet'],
      ['\\uD83E\\uDD8A', 'fox animal'],
      ['\\uD83D\\uDC3B', 'bear animal'],
      ['\\uD83D\\uDC3C', 'panda animal'],
      ['\\uD83D\\uDC28', 'koala animal'],
      ['\\uD83D\\uDC2F', 'tiger animal'],
      ['\\uD83E\\uDD81', 'lion animal'],
      ['\\uD83D\\uDC2E', 'cow animal'],
      ['\\uD83D\\uDC37', 'pig animal'],
      ['\\uD83D\\uDC38', 'frog animal'],
      ['\\uD83D\\uDC35', 'monkey animal'],
      ['\\uD83D\\uDC14', 'chicken bird'],
      ['\\uD83D\\uDC27', 'penguin bird'],
      ['\\uD83D\\uDC26', 'bird animal'],
      ['\\uD83E\\uDD86', 'duck bird'],
      ['\\uD83E\\uDD85', 'eagle bird'],
      ['\\uD83E\\uDD89', 'owl night bird'],
      ['\\uD83E\\uDD87', 'bat night animal'],
      ['\\uD83D\\uDC3A', 'wolf animal'],
      ['\\uD83D\\uDC17', 'boar animal'],
      ['\\uD83D\\uDC34', 'horse animal'],
      ['\\uD83E\\uDD84', 'unicorn fantasy'],
      ['\\uD83D\\uDC1D', 'bee insect'],
      ['\\uD83E\\uDD8B', 'butterfly insect'],
      ['\\uD83D\\uDC1B', 'bug insect'],
      ['\\uD83D\\uDC1C', 'ant insect'],
      ['\\uD83D\\uDC1E', 'ladybug insect'],
      ['\\uD83E\\uDD97', 'cricket insect'],
      ['\\uD83D\\uDD77\\uFE0F', 'spider insect'],
      ['\\uD83D\\uDD78\\uFE0F', 'spider web'],
      ['\\uD83D\\uDC22', 'turtle animal'],
      ['\\uD83D\\uDC0D', 'snake animal'],
      ['\\uD83E\\uDD8E', 'lizard animal'],
      ['\\uD83E\\uDD96', 'dinosaur trex'],
      ['\\uD83E\\uDD95', 'dinosaur sauropod'],
      ['\\uD83D\\uDC19', 'octopus animal'],
      ['\\uD83E\\uDD91', 'squid animal'],
      ['\\uD83E\\uDD90', 'shrimp food'],
      ['\\uD83E\\uDD9E', 'lobster food'],
      ['\\uD83E\\uDD80', 'crab food'],
      ['\\uD83D\\uDC21', 'fish animal'],
      ['\\uD83D\\uDC20', 'tropical fish'],
      ['\\uD83D\\uDC2C', 'dolphin animal'],
      ['\\uD83D\\uDC33', 'whale animal'],
      ['\\uD83D\\uDC0B', 'whale animal'],
      ['\\uD83E\\uDD88', 'shark animal'],
      ['\\uD83D\\uDC0A', 'crocodile animal'],
      ['\\uD83D\\uDC06', 'leopard animal'],
      ['\\uD83D\\uDC05', 'tiger animal'],
      ['\\uD83D\\uDC03', 'buffalo animal'],
      ['\\uD83D\\uDC02', 'ox animal'],
      ['\\uD83D\\uDC04', 'cow animal'],
      ['\\uD83D\\uDC0E', 'horse animal'],
      ['\\uD83D\\uDC16', 'pig animal'],
      ['\\uD83D\\uDC0F', 'ram animal'],
      ['\\uD83D\\uDC11', 'sheep animal'],
      ['\\uD83D\\uDC10', 'goat animal'],
      ['\\uD83D\\uDC2A', 'camel animal'],
      ['\\uD83D\\uDC18', 'elephant animal'],
      ['\\uD83E\\uDD8F', 'rhino animal'],
      ['\\uD83E\\uDD9B', 'hippo animal'],
      ['\\uD83D\\uDC3F\\uFE0F', 'chipmunk animal'],
      ['\\uD83E\\uDD94', 'hedgehog animal'],
      ['\\uD83C\\uDF4F', 'apple fruit food'],
      ['\\uD83C\\uDF4E', 'apple fruit food'],
      ['\\uD83C\\uDF50', 'pear fruit food'],
      ['\\uD83C\\uDF4A', 'orange fruit food'],
      ['\\uD83C\\uDF4B', 'lemon fruit food'],
      ['\\uD83C\\uDF4C', 'banana fruit food'],
      ['\\uD83C\\uDF49', 'watermelon fruit food'],
      ['\\uD83C\\uDF47', 'grapes fruit food'],
      ['\\uD83C\\uDF53', 'strawberry fruit food'],
      ['\\uD83E\\uDD5D', 'kiwi fruit food'],
      ['\\uD83C\\uDF52', 'cherries fruit food'],
      ['\\uD83C\\uDF51', 'peach fruit food'],
      ['\\uD83E\\uDD6D', 'mango fruit food'],
      ['\\uD83C\\uDF4D', 'pineapple fruit food'],
      ['\\uD83E\\uDD65', 'coconut fruit food'],
      ['\\uD83E\\uDD51', 'avocado food'],
      ['\\uD83E\\uDD66', 'broccoli food'],
      ['\\uD83E\\uDD6C', 'leafy green food'],
      ['\\uD83E\\uDD52', 'cucumber food'],
      ['\\uD83C\\uDF36\\uFE0F', 'pepper spicy food'],
      ['\\uD83C\\uDF46', 'eggplant food'],
      ['\\uD83E\\uDD54', 'potato food'],
      ['\\uD83C\\uDF5E', 'bread food'],
      ['\\uD83E\\uDD50', 'croissant food'],
      ['\\uD83E\\uDD56', 'baguette food'],
      ['\\uD83E\\uDD68', 'pretzel food'],
      ['\\uD83E\\uDD6F', 'bagel food'],
      ['\\uD83E\\uDD5E', 'pancakes food'],
      ['\\uD83E\\uDDC0', 'cheese food'],
      ['\\uD83C\\uDF56', 'meat food'],
      ['\\uD83C\\uDF57', 'chicken food'],
      ['\\uD83E\\uDD69', 'steak food'],
      ['\\uD83E\\uDD53', 'bacon food'],
      ['\\uD83C\\uDF73', 'cooking breakfast food'],
      ['\\uD83E\\uDD58', 'paella food'],
      ['\\uD83C\\uDF72', 'pot food soup'],
      ['\\uD83E\\uDD63', 'bowl spoon food'],
      ['\\uD83E\\uDD57', 'salad food'],
      ['\\uD83C\\uDF7F', 'popcorn snack'],
      ['\\uD83E\\uDD6B', 'canned food'],
      ['\\uD83C\\uDF71', 'bento food'],
      ['\\uD83C\\uDF63', 'sushi food'],
      ['\\uD83C\\uDF5C', 'ramen noodles food'],
      ['\\uD83C\\uDF5D', 'spaghetti pasta food'],
      ['\\uD83C\\uDF6A', 'cookie dessert'],
      ['\\uD83C\\uDF69', 'donut dessert'],
      ['\\uD83C\\uDF66', 'ice cream dessert'],
      ['\\uD83C\\uDF70', 'cake dessert'],
      ['\\uD83C\\uDF6B', 'chocolate dessert'],
      ['\\uD83C\\uDF6C', 'candy dessert'],
      ['\\uD83C\\uDF6D', 'lollipop dessert'],
      ['\\u26BD', 'soccer sport'],
      ['\\uD83C\\uDFC0', 'basketball sport'],
      ['\\uD83C\\uDFC8', 'football sport'],
      ['\\u26BE', 'baseball sport'],
      ['\\uD83E\\uDD4E', 'softball sport'],
      ['\\uD83C\\uDFBE', 'tennis sport'],
      ['\\uD83C\\uDFD0', 'volleyball sport'],
      ['\\uD83C\\uDFC9', 'rugby sport'],
      ['\\uD83E\\uDD4F', 'lacrosse sport'],
      ['\\uD83C\\uDFB1', 'pool billiards game'],
      ['\\uD83C\\uDFB3', 'bowling sport'],
      ['\\u26F3', 'golf sport'],
      ['\\uD83C\\uDFA3', 'fishing activity'],
      ['\\uD83E\\uDD4A', 'boxing sport'],
      ['\\uD83E\\uDD4B', 'martial arts sport'],
      ['\\u26F8\\uFE0F', 'ice skating sport'],
      ['\\uD83C\\uDFBF', 'ski sport'],
      ['\\uD83C\\uDFC2', 'snowboard sport'],
      ['\\uD83C\\uDFC4', 'surf sport'],
      ['\\uD83C\\uDFCA', 'swim sport'],
      ['\\uD83C\\uDFCB\\uFE0F', 'weight lifting sport'],
      ['\\uD83D\\uDEB4', 'cycling sport'],
      ['\\uD83E\\uDDD8', 'meditation yoga'],
      ['\\uD83C\\uDFA8', 'art palette creative'],
      ['\\uD83E\\uDDF5', 'thread sewing craft'],
      ['\\uD83E\\uDDF6', 'yarn craft'],
      ['\\uD83C\\uDFAD', 'theater masks activity'],
      ['\\uD83C\\uDFB2', 'dice game'],
      ['\\u265F\\uFE0F', 'chess game'],
      ['\\uD83C\\uDCCF', 'joker card game'],
      ['\\uD83D\\uDE95', 'taxi travel'],
      ['\\uD83D\\uDE99', 'suv car travel'],
      ['\\uD83D\\uDE98', 'car travel'],
      ['\\uD83D\\uDE9B', 'truck travel'],
      ['\\uD83D\\uDE9C', 'tractor travel'],
      ['\\uD83C\\uDFCE\\uFE0F', 'race car travel'],
      ['\\uD83D\\uDEF5', 'scooter travel'],
      ['\\uD83C\\uDFCD\\uFE0F', 'motorcycle travel'],
      ['\\uD83D\\uDEF6', 'canoe boat travel'],
      ['\\u26F5', 'sailboat travel'],
      ['\\uD83D\\uDEA4', 'speedboat travel'],
      ['\\uD83D\\uDEF3\\uFE0F', 'ship travel'],
      ['\\uD83D\\uDE81', 'helicopter travel'],
      ['\\uD83D\\uDE82', 'train travel'],
      ['\\uD83D\\uDE87', 'metro train travel'],
      ['\\uD83D\\uDE89', 'station travel'],
      ['\\uD83C\\uDFE5', 'hospital place'],
      ['\\uD83C\\uDFE6', 'bank place'],
      ['\\uD83C\\uDFE8', 'hotel place'],
      ['\\uD83C\\uDFEB', 'school place'],
      ['\\uD83C\\uDFEC', 'store place'],
      ['\\uD83C\\uDFEF', 'castle place'],
      ['\\uD83D\\uDDFD', 'statue place'],
      ['\\u26EA', 'church place'],
      ['\\uD83C\\uDFD9\\uFE0F', 'cityscape place'],
      ['\\uD83C\\uDFE1', 'house garden home'],
      ['\\uD83C\\uDFDA\\uFE0F', 'ruins place'],
      ['\\uD83C\\uDFDD\\uFE0F', 'island place'],
      ['\\uD83C\\uDFDE\\uFE0F', 'mountain park place'],
      ['\\uD83C\\uDFDF\\uFE0F', 'stadium place'],
      ['\\uD83D\\uDDBC\\uFE0F', 'picture art object'],
      ['\\uD83D\\uDCC0', 'dvd media object'],
      ['\\uD83D\\uDCBE', 'floppy save object'],
      ['\\uD83D\\uDCBF', 'disc media object'],
      ['\\uD83D\\uDCE0', 'fax object'],
      ['\\u260E\\uFE0F', 'phone object'],
      ['\\uD83D\\uDD0E', 'magnifier search object'],
      ['\\uD83D\\uDD66', 'candle light object'],
      ['\\uD83D\\uDED2', 'shopping cart object'],
      ['\\uD83D\\uDD28', 'hammer tool object'],
      ['\\u2692\\uFE0F', 'hammer pick tool object'],
      ['\\uD83D\\uDEE0\\uFE0F', 'hammer wrench tools object'],
      ['\\uD83D\\uDDE1\\uFE0F', 'dagger object'],
      ['\\u2694\\uFE0F', 'crossed swords object'],
      ['\\uD83D\\uDD2B', 'water pistol object'],
      ['\\uD83D\\uDD2E', 'crystal ball object'],
      ['\\uD83D\\uDFF0', 'magic wand object'],
      ['\\uD83E\\uDDFF', 'nazar amulet object'],
      ['\\uD83D\\uDCFF', 'prayer beads object'],
      ['\\u2697\\uFE0F', 'alembic science object'],
      ['\\u2696\\uFE0F', 'scale balance object'],
      ['\\uD83D\\uDD17', 'link symbol'],
      ['\\uD83D\\uDCCE', 'paperclip object'],
      ['\\uD83D\\uDCCC', 'pushpin object'],
      ['\\u2702\\uFE0F', 'scissors object'],
      ['\\uD83D\\uDD8A\\uFE0F', 'pen object'],
      ['\\u270F\\uFE0F', 'pencil object'],
      ['\\uD83D\\uDCD6', 'book object'],
      ['\\uD83D\\uDCDA', 'books object'],
      ['\\uD83D\\uDD2F', 'six pointed star symbol'],
      ['\\u271D\\uFE0F', 'cross symbol'],
      ['\\u262E\\uFE0F', 'peace symbol'],
      ['\\u262F\\uFE0F', 'yin yang symbol'],
      ['\\u267B\\uFE0F', 'recycle symbol'],
      ['\\u267E\\uFE0F', 'infinity symbol'],
      ['\\u2714\\uFE0F', 'check mark symbol'],
      ['\\u2611\\uFE0F', 'checkbox symbol'],
      ['\\u274E', 'x negative symbol'],
      ['\\u2795', 'plus symbol'],
      ['\\u2796', 'minus symbol'],
      ['\\u2797', 'divide symbol'],
      ['\\u2716\\uFE0F', 'multiply symbol'],
      ['\\u3030\\uFE0F', 'wavy dash symbol'],
      ['\\u00A9\\uFE0F', 'copyright symbol'],
      ['\\u00AE\\uFE0F', 'registered symbol'],
      ['\\u2122\\uFE0F', 'trademark symbol']
    );
    emojiCatalog.push(
      ['\\uD83E\\uDD70', 'smiling hearts affection crush'],
      ['\\uD83E\\uDD72', 'smiling tear bittersweet'],
      ['\\uD83D\\uDE0C', 'relieved calm peaceful'],
      ['\\uD83D\\uDE0B', 'yum tasty delicious'],
      ['\\uD83D\\uDE0F', 'smirk playful suggestive'],
      ['\\uD83D\\uDE43', 'upside down silly sarcasm'],
      ['\\uD83E\\uDD24', 'drooling face hungry'],
      ['\\uD83E\\uDD2F', 'mind blown shocked'],
      ['\\uD83E\\uDD2C', 'swearing angry censored'],
      ['\\uD83E\\uDD74', 'woozy dizzy drunk'],
      ['\\uD83E\\uDD11', 'money face rich'],
      ['\\uD83E\\uDEE5', 'dotted line invisible hidden'],
      ['\\uD83E\\uDD7A', 'pleading please cute'],
      ['\\uD83E\\uDEF6', 'heart hands love support'],
      ['\\uD83E\\uDEF0', 'hand fingers heart'],
      ['\\uD83E\\uDD0C', 'pinched fingers gesture'],
      ['\\uD83E\\uDD1F', 'love you gesture'],
      ['\\uD83E\\uDD18', 'rock on horns'],
      ['\\uD83D\\uDD95', 'middle finger rude'],
      ['\\uD83D\\uDC4A', 'fist bump punch'],
      ['\\uD83E\\uDD1C', 'right fist bump'],
      ['\\uD83E\\uDD1B', 'left fist bump'],
      ['\\uD83D\\uDD96', 'vulcan salute'],
      ['\\uD83D\\uDC8B', 'kiss mark'],
      ['\\uD83D\\uDC44', 'mouth lips'],
      ['\\uD83E\\uDDE0', 'brain smart'],
      ['\\uD83E\\uDEC0', 'heart organ health'],
      ['\\uD83E\\uDEC1', 'lungs air health'],
      ['\\uD83D\\uDC43', 'nose smell'],
      ['\\uD83E\\uDDB7', 'tooth dentist'],
      ['\\uD83D\\uDC0C', 'snail slow'],
      ['\\uD83E\\uDD9F', 'mosquito insect'],
      ['\\uD83E\\uDED0', 'blueberries fruit food'],
      ['\\uD83C\\uDF48', 'melon fruit food'],
      ['\\uD83E\\uDED2', 'olive food'],
      ['\\uD83E\\uDD55', 'carrot food'],
      ['\\uD83C\\uDF3D', 'corn food'],
      ['\\uD83C\\uDF60', 'sweet potato food'],
      ['\\uD83E\\uDDC7', 'waffle food'],
      ['\\uD83C\\uDF54', 'burger food'],
      ['\\uD83C\\uDF5F', 'fries food'],
      ['\\uD83C\\uDF55', 'pizza food'],
      ['\\uD83C\\uDF2D', 'hot dog food'],
      ['\\uD83C\\uDF2E', 'taco food'],
      ['\\uD83C\\uDF2F', 'burrito food'],
      ['\\uD83E\\uDD59', 'stuffed flatbread food'],
      ['\\uD83E\\uDDC6', 'falafel food'],
      ['\\uD83E\\uDD5A', 'egg food'],
      ['\\uD83E\\uDED5', 'fondue food'],
      ['\\uD83C\\uDF75', 'tea drink'],
      ['\\uD83E\\uDDCB', 'bubble tea drink'],
      ['\\uD83E\\uDDC3', 'cup drink'],
      ['\\uD83E\\uDD42', 'cheers drink'],
      ['\\uD83C\\uDF79', 'cocktail drink'],
      ['\\uD83C\\uDF78', 'tropical drink'],
      ['\\uD83C\\uDF76', 'sake drink'],
      ['\\uD83E\\uDDC9', 'mate drink'],
      ['\\uD83D\\uDECC', 'sleep bed rest'],
      ['\\uD83E\\uDD71', 'yawn tired'],
      ['\\uD83E\\uDEAB', 'low battery power'],
      ['\\uD83E\\uDEAC', 'smoking smoke'],
      ['\\uD83E\\uDEB5', 'wood log fireplace'],
      ['\\uD83E\\uDEB6', 'feather light'],
      ['\\uD83E\\uDEBA', 'nest empty'],
      ['\\uD83E\\uDEB9', 'nest eggs'],
      ['\\uD83E\\uDEBB', 'x ray health'],
      ['\\uD83E\\uDEBC', 'crutch health'],
      ['\\uD83D\\uDE9F', 'suspension railway travel'],
      ['\\uD83D\\uDEA0', 'mountain railway travel'],
      ['\\uD83D\\uDEA1', 'aerial tramway travel'],
      ['\\uD83D\\uDEA2', 'ship travel'],
      ['\\uD83D\\uDEE9\\uFE0F', 'small airplane travel'],
      ['\\uD83D\\uDEF0\\uFE0F', 'satellite space'],
      ['\\uD83C\\uDFA1', 'ferris wheel activity'],
      ['\\uD83C\\uDFA2', 'roller coaster activity'],
      ['\\uD83C\\uDFAA', 'circus tent activity'],
      ['\\uD83C\\uDFA4', 'microphone music'],
      ['\\uD83C\\uDFA7', 'headphones audio'],
      ['\\uD83E\\uDD41', 'drum music'],
      ['\\uD83C\\uDFB7', 'saxophone music'],
      ['\\uD83C\\uDFB8', 'guitar music'],
      ['\\uD83C\\uDFB9', 'piano music'],
      ['\\uD83C\\uDFBA', 'trumpet music'],
      ['\\uD83C\\uDFBB', 'violin music'],
      ['\\uD83E\\uDE87', 'maracas music'],
      ['\\uD83E\\uDE88', 'flute music'],
      ['\\uD83D\\uDC8E', 'gem diamond value'],
      ['\\uD83E\\uDFF7\\uFE0F', 'label tag'],
      ['\\uD83E\\uDDFE', 'receipt cost'],
      ['\\uD83D\\uDCE7', 'email message'],
      ['\\uD83D\\uDCE8', 'incoming mail'],
      ['\\uD83D\\uDCE9', 'outgoing mail'],
      ['\\uD83D\\uDCEB', 'mailbox flag'],
      ['\\uD83D\\uDCEF', 'postal horn'],
      ['\\uD83D\\uDD75\\uFE0F', 'detective investigate'],
      ['\\uD83E\\uDD77', 'ninja stealth'],
      ['\\uD83E\\uDDD1\\u200D\\uD83D\\uDD27', 'mechanic repair'],
      ['\\uD83E\\uDDD1\\u200D\\uD83D\\uDCBB', 'technologist computer'],
      ['\\uD83E\\uDDD1\\u200D\\uD83C\\uDF73', 'cook kitchen'],
      ['\\uD83E\\uDDD1\\u200D\\uD83C\\uDF3E', 'farmer garden'],
      ['\\uD83E\\uDDD1\\u200D\\uD83D\\uDE92', 'firefighter safety'],
      ['\\uD83E\\uDDD1\\u200D\\uD83D\\uDE80', 'astronaut space'],
      ['\\uD83E\\uDDD9', 'mage magic'],
      ['\\uD83E\\uDDDB', 'vampire spooky'],
      ['\\uD83E\\uDDDF', 'zombie spooky'],
      ['\\uD83E\\uDDDC', 'merperson fantasy'],
      ['\\uD83E\\uDDDD', 'elf fantasy'],
      ['\\uD83E\\uDDDE', 'genie fantasy']
    );
    const emojiLibrary = [];
    const seenEmoji = new Set();
    for (const entry of emojiCatalog) {{
      if (seenEmoji.has(entry[0])) continue;
      seenEmoji.add(entry[0]);
      emojiLibrary.push(entry);
    }}
    const emojiTabs = [
      ['most', 'Most used'],
      ['common', 'Common'],
      ['smileys', 'Smileys'],
      ['people', 'People'],
      ['nature', 'Nature'],
      ['food', 'Food'],
      ['activity', 'Activity'],
      ['places', 'Places'],
      ['objects', 'Objects'],
      ['symbols', 'Symbols'],
      ['smart', 'Smart home'],
      ['all', 'All'],
    ];
    const mostUsedEmoji = new Set([
      '\\u2764\\uFE0F', '\\uD83D\\uDE02', '\\uD83E\\uDD23', '\\uD83D\\uDE0D', '\\uD83D\\uDE2D',
      '\\uD83D\\uDE0A', '\\uD83D\\uDE09', '\\uD83D\\uDE08', '\\uD83D\\uDCA4', '\\uD83D\\uDE34',
      '\\uD83D\\uDD25', '\\u2728', '\\uD83D\\uDC4D', '\\uD83D\\uDE4F', '\\u2705', '\\u274C',
      '\\uD83D\\uDC40', '\\uD83E\\uDD14', '\\uD83D\\uDE44', '\\uD83C\\uDF89', '\\u2B50',
      '\\uD83D\\uDCAF', '\\uD83D\\uDCA1', '\\uD83D\\uDD14', '\\u26A0\\uFE0F', '\\uD83C\\uDF21\\uFE0F'
    ]);

    function emojiCategory(name, emoji) {{
      if (mostUsedEmoji.has(emoji)) return 'most';
      if (/(laugh|smile|face|cry|sad|angry|wink|devil|angel|kiss|thinking|sick|tired|sleep|tears|cool|party|heart|love|thumbs|clap|pray|hands|skull|ghost|poop|ok hand|peace|fingers|handshake)/.test(name)) return 'smileys';
      if (/(person|people|family|user|presence|running|motion|cycling|swim|lifting|meditation|yoga|shirt|socks)/.test(name)) return 'people';
      if (/(animal|pet|dog|cat|bird|tree|leaf|plant|flower|garden|weather|rain|sun|moon|snow|storm|cloud|wind|water|wave|insect|fish|dinosaur|shark|whale)/.test(name)) return 'nature';
      if (/(food|fruit|drink|coffee|beer|wine|kitchen|pizza|cake|candy|dessert|bread|meat|sushi|ramen|salad)/.test(name)) return 'food';
      if (/(sport|game|activity|art|craft|music|movie|media|theater|dice|chess|fishing)/.test(name)) return 'activity';
      if (/(travel|place|car|truck|train|airplane|hotel|city|house|home|garage|office|school|store|castle|island|mountain|road|fuel|bus|bike|ship|boat)/.test(name)) return 'places';
      if (/(object|tool|phone|computer|watch|keyboard|camera|book|document|clipboard|calendar|money|card|battery|plug|speaker|trash|clean|bathroom|laundry|timer|clock|search|pin|map|gear|settings)/.test(name)) return 'objects';
      if (/(symbol|circle|arrow|check|x |plus|minus|question|exclamation|copyright|registered|trademark|recycle|infinity|peace|yin yang|star|status|on active|back|end|top)/.test(name)) return 'symbols';
      if (/(light|switch|toggle|power|sensor|thermostat|climate|lock|unlock|security|alarm|siren|door|window|wifi|network|server|automation|energy|electricity|outlet|garage)/.test(name)) return 'smart';
      return 'common';
    }}

    function emojiMatchesTab(entry, tab) {{
      const emoji = entry[0];
      const name = entry[1];
      if (tab === 'all') return true;
      if (tab === 'most') return mostUsedEmoji.has(emoji);
      if (tab === 'common') return ['smileys', 'symbols'].includes(emojiCategory(name, emoji));
      return emojiCategory(name, emoji) === tab;
    }}
    let itemPreviewTimer = null;
    let groupPreviewTimer = null;
    let itemPreviewRequest = 0;
    let groupPreviewRequest = 0;
    let editingItemId = null;
    let editingGroupId = null;
    const suggestionState = new WeakMap();
    const caretPositions = new WeakMap();
    const initialDashboard = {dashboard_json};
    dashboard.value = JSON.stringify(initialDashboard, null, 2);
    lastSavedDashboard = dashboard.value;

    function bindButton(button, handler) {{
      button.type = 'button';
      let lastTouch = 0;
      let touchStartX = 0;
      let touchStartY = 0;
      let touchMoved = false;
      button.addEventListener('touchstart', (event) => {{
        const touch = event.changedTouches && event.changedTouches[0];
        if (!touch) return;
        touchStartX = touch.clientX;
        touchStartY = touch.clientY;
        touchMoved = false;
      }}, {{ passive: true }});
      button.addEventListener('touchmove', (event) => {{
        const touch = event.changedTouches && event.changedTouches[0];
        if (!touch) return;
        if (Math.abs(touch.clientX - touchStartX) > 8 || Math.abs(touch.clientY - touchStartY) > 8) {{
          touchMoved = true;
        }}
      }}, {{ passive: true }});
      button.addEventListener('touchend', (event) => {{
        lastTouch = Date.now();
        if (touchMoved) {{
          event.stopPropagation();
          return;
        }}
        event.preventDefault();
        event.stopPropagation();
        handler(event);
      }}, {{ passive: false }});
      button.addEventListener('click', (event) => {{
        event.preventDefault();
        event.stopPropagation();
        if (Date.now() - lastTouch < 700) return;
        handler(event);
      }});
    }}

    function setStatus(message, isError = false, localTarget = '') {{
      statusEl.textContent = message;
      statusEl.classList.toggle('error', Boolean(isError));
      const target = localStatusTargets[localTarget];
      if (target) {{
        target.textContent = message;
        target.classList.toggle('error', Boolean(isError));
      }}
    }}

    window.addEventListener('error', (event) => {{
      setStatus('Builder error: ' + event.message, true);
    }});
    window.addEventListener('unhandledrejection', (event) => {{
      const reason = event.reason && event.reason.message ? event.reason.message : String(event.reason);
      setStatus('Builder error: ' + reason, true);
    }});

    function readDashboard() {{
      return JSON.parse(dashboard.value);
    }}

    function escapeForHtml(value) {{
      return String(value).replace(/[&<>]/g, (char) => ({{
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
      }}[char]));
    }}

    function updateJsonHighlight() {{
      const source = dashboard.value;
      try {{
        JSON.parse(source);
        jsonHighlight.innerHTML = escapeForHtml(source).replace(
          /("(?:\\\\.|[^"\\\\])*"\\s*:)|("(?:\\\\.|[^"\\\\])*")|\\b(true|false)\\b|\\b(null)\\b|-?\\b\\d+(?:\\.\\d+)?(?:[eE][+-]?\\d+)?\\b/g,
          (match, key, stringValue, booleanValue, nullValue) => {{
            if (key) return '<span class="json-key">' + key + '</span>';
            if (stringValue) return '<span class="json-string">' + stringValue + '</span>';
            if (booleanValue) return '<span class="json-boolean">' + booleanValue + '</span>';
            if (nullValue) return '<span class="json-null">' + nullValue + '</span>';
            return '<span class="json-number">' + match + '</span>';
          }}
        );
      }} catch (err) {{
        jsonHighlight.textContent = source;
      }}
    }}

    function syncDashboardFromEditor() {{
      dashboard.value = jsonHighlight.textContent;
    }}

    function cleanBaseUrl() {{
      return baseUrlInput.value.trim().replace(/\\/$/, '');
    }}

    function refreshSetupUrls() {{
      const clean = cleanBaseUrl();
      const parsed = readDashboard();
      apiUrl.value = clean + '/api';
      configUrl.value = clean + '/api/homeassistant_garmin/garminhomeassistant/config/' + parsed.setup_code;
    }}

    function localConfigUrl() {{
      const parsed = readDashboard();
      return window.location.origin + '/api/homeassistant_garmin/garminhomeassistant/config/' + parsed.setup_code;
    }}

    async function copyText(text) {{
      if (navigator.clipboard && window.isSecureContext) {{
        await navigator.clipboard.writeText(text);
        return;
      }}

      const scratch = document.createElement('textarea');
      scratch.value = text;
      scratch.setAttribute('readonly', '');
      scratch.style.position = 'fixed';
      scratch.style.left = '-9999px';
      scratch.style.top = '0';
      document.body.appendChild(scratch);
      scratch.focus();
      scratch.select();
      const copied = document.execCommand('copy');
      document.body.removeChild(scratch);
      if (!copied) throw new Error('Clipboard copy was blocked by the browser');
    }}

    function showCopyPanel(title, text, copied) {{
      copyPanelTitle.textContent = title;
      copyPanelHelp.textContent = copied
        ? 'Copied automatically. The value is also selected here in case the browser blocked the clipboard silently.'
        : 'The browser blocked automatic copy. Press Ctrl+C to copy the selected value.';
      copyPanelValue.value = text;
      copyPanel.hidden = false;
      copyPanelValue.focus();
      copyPanelValue.select();
    }}

    async function copyWithPanel(title, text) {{
      let copied = false;
      try {{
        await copyText(text);
        copied = true;
      }} catch (err) {{
        copied = false;
      }}
      showCopyPanel(title, text, copied);
      return copied;
    }}

    function updateUnsavedBar() {{
      const dirty = Boolean(lastSavedDashboard) && dashboard.value !== lastSavedDashboard;
      unsavedBar.classList.toggle('visible', dirty);
    }}

    function writeDashboard(value) {{
      dashboard.value = JSON.stringify(value, null, 2);
      baseUrlInput.value = (value.base_url || '{escaped_base_url}').replace(/\\/$/, '');
      refreshGroupOptions();
      renderItems();
      refreshSetupUrls();
      syncGlanceControls(value);
      updateJsonHighlight();
      if (!suppressDirtyState) updateUnsavedBar();
    }}

    function syncGlanceControls(value) {{
      const glance = value.glance || {{}};
      glanceType.value = glance.type || 'status';
      glanceContent.value = glance.content || '';
      updateGlanceVisibility();
    }}

    function updateGlanceVisibility() {{
      const isCustom = glanceType.value === 'info';
      glanceTemplateField.hidden = !isCustom;
    }}

    function updateGlanceJson(showStatus = true) {{
      try {{
        const parsed = readDashboard();
        parsed.glance = {{
          type: glanceType.value,
          content: glanceType.value === 'info' ? glanceContent.value.trim() : '',
        }};
        writeDashboard(parsed);
        if (showStatus) setStatus('Glance updated. Save dashboard to publish it.', false, 'glance');
      }} catch (err) {{
        if (showStatus) setStatus('Glance update failed: ' + err.message, true, 'glance');
      }}
    }}

    async function saveDashboard(localTarget = 'save', successMessage = 'Dashboard saved.') {{
      setStatus('Saving...', false, localTarget);
      let parsed;
      try {{
        parsed = JSON.parse(dashboard.value);
      }} catch (err) {{
        setStatus('Invalid JSON: ' + err.message, true, localTarget);
        return false;
      }}

      const response = await fetch('{GARMIN_HOMEASSISTANT_DASHBOARD_PATH}', {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
        }},
        body: JSON.stringify(parsed),
      }});

      if (!response.ok) {{
        setStatus('Save failed: HTTP ' + response.status, true, localTarget);
        return false;
      }}

      const saved = await response.json();
      suppressDirtyState = true;
      writeDashboard(saved);
      suppressDirtyState = false;
      lastSavedDashboard = dashboard.value;
      staleWarning.classList.remove('visible');
      updateUnsavedBar();
      setStatus(successMessage, false, localTarget);
      return true;
    }}

    function slugId(prefix) {{
      return (prefix || 'item')
        .toUpperCase()
        .replace(/[^A-Z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '')
        .slice(0, 24) + '_' + Math.random().toString(36).slice(2, 6).toUpperCase();
    }}

    function optionalNumber(input) {{
      if (input.value.trim() === '') return null;
      const parsed = Number(input.value);
      if (Number.isNaN(parsed)) throw new Error(input.previousElementSibling.textContent + ' must be a number');
      return parsed;
    }}

    function confirmValue() {{
      if (!itemConfirmEnabled.checked) return false;
      return itemConfirmMessage.value.trim() || true;
    }}

    function validateActionData() {{
      const value = itemData.value.trim();
      if (!value) return '';
      const parsed = JSON.parse(value);
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {{
        throw new Error('Custom action data must be a JSON object');
      }}
      return JSON.stringify(parsed);
    }}

    function actionDataWithNumericOptions(baseJson) {{
      let parsed = {{}};
      if (baseJson) parsed = JSON.parse(baseJson);
      if (itemType.value === 'numeric' && numericTransition.value.trim() !== '') {{
        const transition = Number(numericTransition.value);
        if (Number.isNaN(transition) || transition < 0) {{
          throw new Error('Transition seconds must be zero or greater');
        }}
        parsed.transition = transition;
      }}
      return Object.keys(parsed).length ? JSON.stringify(parsed) : '';
    }}

    function allGroups(items, path = []) {{
      let groups = [];
      for (const item of items || []) {{
        if (item.type === 'group') {{
          const nextPath = path.concat(item.id);
          groups.push({{ id: item.id, name: item.name, path: nextPath }});
          groups = groups.concat(allGroups(item.items || [], nextPath));
        }}
      }}
      return groups;
    }}

    function findGroup(items, id) {{
      for (const item of items || []) {{
        if (item.id === id && item.type === 'group') return item;
        const child = findGroup(item.items || [], id);
        if (child) return child;
      }}
      return null;
    }}

    function findContainer(items, id) {{
      for (const item of items || []) {{
        if (item.id === id) return items;
        const child = findContainer(item.items || [], id);
        if (child) return child;
      }}
      return null;
    }}

    function findItem(items, id) {{
      for (const item of items || []) {{
        if (item.id === id) return item;
        const child = findItem(item.items || [], id);
        if (child) return child;
      }}
      return null;
    }}

    function renderItems() {{
      let parsed;
      try {{
        parsed = readDashboard();
      }} catch (err) {{
        itemList.textContent = 'Fix JSON to show menu items.';
        return;
      }}
      itemList.innerHTML = '';
      if (!parsed.items || parsed.items.length === 0) {{
        itemList.textContent = 'No items yet. Add an item or submenu above.';
        return;
      }}
      renderItemRows(parsed.items, itemList, 0);
    }}

    function renderItemRows(items, parent, depth) {{
      items.forEach((item, index) => {{
        const row = document.createElement('div');
        const isGroup = item.type === 'group';
        row.className = 'item-row ' + (isGroup ? 'group-row' : 'leaf-row');
        row.style.paddingLeft = (0.5 + depth * 1.3) + 'rem';

        const label = document.createElement('div');
        label.className = 'item-label';
        const badgeClass = isGroup ? 'group-badge' : 'item-type-badge';
        const badgeText = isGroup ? 'submenu' : (item.type || 'auto');
        const metaText = item.entity_id ? escapeHtml(item.entity_id) : escapeHtml((item.items || []).length + ' item(s)');
        const treePrefix = depth > 0 ? escapeHtml('|  '.repeat(depth - 1) + '|--') : '';
        label.innerHTML = '<span class="tree-prefix">' + treePrefix + '</span>' +
          '<div class="item-main"><span class="item-badge ' + badgeClass + '">' + escapeHtml(badgeText) + '</span>' +
          '<strong class="item-title">' + escapeHtml(item.name || item.entity_id || 'Item') + '</strong>' +
          '<div class="item-meta">' + metaText + '</div></div>';

        const up = document.createElement('button');
        up.className = 'icon-button action-up';
        up.textContent = 'Up';
        up.disabled = index === 0;
        bindButton(up, () => moveItem(item.id, -1));

        const down = document.createElement('button');
        down.className = 'icon-button action-down';
        down.textContent = 'Down';
        down.disabled = index === items.length - 1;
        bindButton(down, () => moveItem(item.id, 1));

        const edit = document.createElement('button');
        edit.className = 'icon-button action-edit';
        edit.textContent = 'Edit';
        bindButton(edit, () => editItem(item.id));

        const remove = document.createElement('button');
        remove.className = 'icon-button action-remove danger';
        remove.textContent = 'Remove';
        bindButton(remove, () => removeItem(item.id));

        const actions = document.createElement('div');
        actions.className = 'item-actions';
        actions.append(up, down, edit, remove);

        row.append(label, actions);
        parent.appendChild(row);

        if (item.type === 'group' && item.items && item.items.length > 0) {{
          renderItemRows(item.items, parent, depth + 1);
        }}
      }});
    }}

    function escapeHtml(value) {{
      return String(value).replace(/[&<>"']/g, (char) => ({{
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }}[char]));
    }}

    function moveItem(id, delta) {{
      try {{
        const parsed = readDashboard();
        const container = findContainer(parsed.items || [], id);
        if (!container) throw new Error('Item not found');
        const index = container.findIndex((item) => item.id === id);
        const nextIndex = index + delta;
        if (nextIndex < 0 || nextIndex >= container.length) return;
        const [item] = container.splice(index, 1);
        container.splice(nextIndex, 0, item);
        writeDashboard(parsed);
        setStatus('Order changed. Save dashboard to publish it.', false, 'save');
      }} catch (err) {{
        setStatus('Move failed: ' + err.message, true, 'save');
      }}
    }}

    function removeItem(id) {{
      try {{
        const parsed = readDashboard();
        const item = findItem(parsed.items || [], id);
        if (!item) throw new Error('Item not found');
        if (!confirm('Remove "' + (item.name || item.entity_id || 'item') + '"?')) return;
        const container = findContainer(parsed.items || [], id);
        const index = container.findIndex((entry) => entry.id === id);
        container.splice(index, 1);
        writeDashboard(parsed);
        setStatus('Item removed. Save dashboard to publish it.', false, 'save');
      }} catch (err) {{
        setStatus('Remove failed: ' + err.message, true, 'save');
      }}
    }}

    function refreshGroupOptions() {{
      let parsed;
      try {{
        parsed = readDashboard();
      }} catch (err) {{
        return;
      }}
      const groups = allGroups(parsed.items || []);
      for (const select of [parentGroup, groupParent]) {{
        const current = select.value;
        select.innerHTML = '<option value="">Top level</option>';
        for (const group of groups) {{
          const option = document.createElement('option');
          option.value = group.id;
          option.textContent = group.name;
          select.appendChild(option);
        }}
        select.value = current;
      }}
    }}

    function addToParent(parsed, parentId, item) {{
      if (!parentId) {{
        parsed.items = parsed.items || [];
        parsed.items.push(item);
        return;
      }}
      const parent = findGroup(parsed.items || [], parentId);
      if (!parent) throw new Error('Parent submenu not found');
      parent.items = parent.items || [];
      parent.items.push(item);
    }}

    function parentIdForItem(items, id, parentId = '') {{
      for (const item of items || []) {{
        if (item.id === id) return parentId;
        const childParent = parentIdForItem(item.items || [], id, item.id);
        if (childParent !== null) return childParent;
      }}
      return null;
    }}

    function resetItemForm() {{
      editingItemId = null;
      entityPicker.value = '';
      itemName.value = '';
      itemContent.value = '';
      itemTemplateResult.textContent = '';
      itemType.value = 'auto';
      parentGroup.value = '';
      itemEnabled.checked = true;
      itemPin.checked = false;
      itemExit.checked = false;
      itemConfirmEnabled.checked = false;
      itemConfirmMessage.value = '';
      itemAction.value = '';
      itemData.value = '';
      numericMin.value = '';
      numericMax.value = '';
      numericStep.value = '';
      numericAttribute.value = '';
      numericDataAttribute.value = '';
      numericTransition.value = '';
      itemSectionTitle.textContent = 'Add Item';
      addItemButton.textContent = 'Add item';
      cancelEditItemButton.style.display = 'none';
      updateBehaviorHelp();
      updateWatchPreview();
    }}

    function resetGroupForm() {{
      editingGroupId = null;
      groupName.value = '';
      groupContent.value = '';
      groupTemplateResult.textContent = '';
      groupParent.value = '';
      groupTitle.value = '';
      groupEnabled.checked = true;
      groupSectionTitle.textContent = 'Add Submenu';
      addGroupButton.textContent = 'Add submenu';
      cancelEditGroupButton.style.display = 'none';
    }}

    function editItem(id) {{
      let parsed;
      try {{
        parsed = readDashboard();
      }} catch (err) {{
        setStatus('Edit failed: fix JSON first.', true, 'item');
        return;
      }}
      const item = findItem(parsed.items || [], id);
      if (!item) {{
        setStatus('Edit failed: item not found.', true, 'item');
        return;
      }}
      if (item.type === 'group') {{
        editingGroupId = id;
        groupName.value = item.name || '';
        groupContent.value = item.content || '';
        groupParent.value = parentIdForItem(parsed.items || [], id) || '';
        groupTitle.value = item.title || item.name || '';
        groupEnabled.checked = item.enabled !== false;
        groupSectionTitle.textContent = 'Edit Submenu';
        addGroupButton.textContent = 'Update submenu';
        cancelEditGroupButton.style.display = 'inline-block';
      scheduleGroupTemplatePreview();
      groupPanel.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      groupName.focus();
      setStatus('Editing submenu. Update submenu, then save dashboard.');
        return;
      }}
      editingItemId = id;
      entityPicker.value = item.entity_id || '';
      itemName.value = item.name || '';
      itemContent.value = item.content || '';
      itemType.value = item.type || 'auto';
      parentGroup.value = parentIdForItem(parsed.items || [], id) || '';
      itemEnabled.checked = item.enabled !== false;
      itemPin.checked = Boolean(item.pin);
      itemExit.checked = Boolean(item.exit);
      itemConfirmEnabled.checked = Boolean(item.confirm);
      itemConfirmMessage.value = typeof item.confirm === 'string' ? item.confirm : '';
      itemAction.value = item.tap_action_action || '';
      itemData.value = item.tap_action_data || '';
      numericMin.value = item.numeric_min ?? '';
      numericMax.value = item.numeric_max ?? '';
      numericStep.value = item.numeric_step ?? '';
      numericAttribute.value = item.numeric_attribute || '';
      numericDataAttribute.value = item.numeric_data_attribute || '';
      try {{
        const existingActionData = item.tap_action_data ? JSON.parse(item.tap_action_data) : {{}};
        numericTransition.value = existingActionData.transition ?? '';
      }} catch (err) {{
        numericTransition.value = '';
      }}
      itemSectionTitle.textContent = 'Edit Item';
      addItemButton.textContent = 'Update item';
      cancelEditItemButton.style.display = 'inline-block';
      updateBehaviorHelp();
      scheduleItemTemplatePreview();
      updateWatchPreview();
      itemPanel.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      entityPicker.focus();
      setStatus('Editing item. Update item, then save dashboard.');
    }}

    function updateExistingItem(parsed, id, values) {{
      const item = findItem(parsed.items || [], id);
      if (!item) throw new Error('Item not found');
      const currentParent = parentIdForItem(parsed.items || [], id) || '';
      Object.assign(item, values, {{
        id,
        items: item.items || [],
      }});
      if (parentGroup.value === currentParent) return;
      const container = findContainer(parsed.items || [], id);
      if (!container) throw new Error('Item container not found');
      const index = container.findIndex((entry) => entry.id === id);
      const [moved] = container.splice(index, 1);
      addToParent(parsed, parentGroup.value, moved);
    }}

    function updateExistingGroup(parsed, id, values) {{
      const item = findItem(parsed.items || [], id);
      if (!item || item.type !== 'group') throw new Error('Submenu not found');
      const currentParent = parentIdForItem(parsed.items || [], id) || '';
      if (groupParent.value === id) throw new Error('A submenu cannot contain itself');
      Object.assign(item, values, {{
        id,
        type: 'group',
        entity_id: '',
        items: item.items || [],
      }});
      if (groupParent.value === currentParent) return;
      if (findItem(item.items || [], groupParent.value)) {{
        throw new Error('A submenu cannot be moved inside its own child');
      }}
      const container = findContainer(parsed.items || [], id);
      if (!container) throw new Error('Submenu container not found');
      const index = container.findIndex((entry) => entry.id === id);
      const [moved] = container.splice(index, 1);
      addToParent(parsed, groupParent.value, moved);
    }}

    function entityMeta(entityId) {{
      return entities.find((entity) => entity.entity_id === entityId);
    }}

    function titleCase(value) {{
      return String(value || '')
        .replace(/_/g, ' ')
        .replace(/\\b\\w/g, (char) => char.toUpperCase());
    }}

    function entityTypeLabel(entity) {{
      if (!entity) return '';
      if (entity.device_class) return titleCase(entity.device_class);
      return titleCase(entity.domain);
    }}

    function entityIcon(entity) {{
      const domain = entity ? entity.domain : '';
      const deviceClass = entity ? entity.device_class : '';
      if (domain === 'light') return '\\uD83D\\uDCA1';
      if (domain === 'fan') return '\\uD83C\\uDF2C\\uFE0F';
      if (domain === 'switch' || domain === 'input_boolean') return '\\u23FB';
      if (domain === 'automation') return '\\u2699\\uFE0F';
      if (domain === 'script') return '\\u25B6\\uFE0F';
      if (domain === 'scene') return '\\uD83C\\uDFAC';
      if (domain === 'cover') return '\\uD83E\\uDE9F';
      if (domain === 'lock') return '\\uD83D\\uDD12';
      if (domain === 'climate') return '\\uD83C\\uDF21\\uFE0F';
      if (domain === 'media_player') return '\\uD83D\\uDCFA';
      if (domain === 'camera') return '\\uD83D\\uDCF7';
      if (domain === 'person') return '\\uD83D\\uDC64';
      if (domain === 'weather') return '\\u26C5';
      if (deviceClass === 'temperature') return '\\uD83C\\uDF21\\uFE0F';
      if (deviceClass === 'humidity' || deviceClass === 'moisture') return '\\uD83D\\uDCA7';
      if (deviceClass === 'battery') return '\\uD83D\\uDD0B';
      if (deviceClass === 'power' || deviceClass === 'energy') return '\\u26A1';
      if (deviceClass === 'door') return '\\uD83D\\uDEAA';
      if (deviceClass === 'window') return '\\uD83E\\uDE9F';
      if (deviceClass === 'motion' || deviceClass === 'occupancy') return '\\uD83C\\uDFC3';
      if (domain === 'binary_sensor') return '\\u2139\\uFE0F';
      if (domain === 'sensor') return '\\uD83D\\uDCCA';
      return '\\u2139\\uFE0F';
    }}

    function updateBehaviorHelp() {{
      const value = itemType.value;
      const meta = entityMeta(entityPicker.value.trim());
      const help = {{
        auto: 'Automatic chooses the GarminHomeAssistant item type from the entity domain. This is best for most users.',
        toggle: 'Toggle is for lights, switches, input booleans, and similar on/off entities. Select the entity first; advanced options are usually not needed.',
        tap: 'Run action is for scripts, scenes, automations, buttons, or custom services. Select an entity first, or enter a Custom action below.',
        info: 'Info only shows a row on the watch without running an action. Secondary text is optional.',
        numeric: 'Number picker needs an entity first, such as a light, fan, cover, media player, climate entity, input_number, or number entity. Defaults are filled from the entity type; use Numeric picker options only to override them.',
      }};
      if (value === 'numeric') {{
        const domain = meta ? meta.domain : '';
        const examples = {{
          light: ' For lights such as light.living_room, leave the override fields blank to use brightness defaults: light.turn_on, brightness, 0-255, step 5.',
          fan: ' For fans, leave overrides blank to use percentage defaults: fan.set_percentage, percentage, 0-100, step 5.',
          cover: ' For covers, leave overrides blank to use position defaults: cover.set_position, position, 0-100, step 5.',
          media_player: ' For media players, leave overrides blank to use volume defaults: media_player.volume_set, volume_level, 0-1, step 0.05.',
          climate: ' For climate entities, leave overrides blank to use temperature defaults: climate.set_temperature, temperature, 50-85, step 1.',
        }};
        itemBehaviorHelp.textContent = help.numeric + (examples[domain] || '');
      }} else {{
        itemBehaviorHelp.textContent = help[value] || help.auto;
      }}
      customActionOptions.hidden = !['tap'].includes(value);
      numericPickerOptions.hidden = value !== 'numeric';
    }}

    function tokenAtCursor(input) {{
      const cursor = input.selectionStart || 0;
      const before = input.value.slice(0, cursor);
      const match = before.match(/[a-zA-Z0-9_\\.]+$/);
      if (!match) return {{ token: '', start: cursor, end: cursor }};
      return {{
        token: match[0],
        start: cursor - match[0].length,
        end: cursor,
      }};
    }}

    function shouldInsertStateSnippet(input, tokenInfo) {{
      if (tokenInfo.token) return false;
      return !input.value.slice(0, input.selectionStart || 0).match(/states\\(['"][^'"]*$/);
    }}

    function applyTemplateSuggestion(input, entityId) {{
      const tokenInfo = tokenAtCursor(input);
      const replacement = shouldInsertStateSnippet(input, tokenInfo)
        ? "{{{{ states('" + entityId + "') }}}}"
        : entityId;
      input.value = input.value.slice(0, tokenInfo.start) + replacement + input.value.slice(tokenInfo.end);
      input.focus();
      input.selectionStart = input.selectionEnd = tokenInfo.start + replacement.length;
      hideTemplateSuggestions();
      if (input === itemContent) scheduleItemTemplatePreview();
      if (input === groupContent) scheduleGroupTemplatePreview();
      if (input === glanceContent) updateGlanceJson(false);
      updateWatchPreview();
    }}

    function hideTemplateSuggestions() {{
      itemTemplateSuggestions.style.display = 'none';
      groupTemplateSuggestions.style.display = 'none';
      glanceTemplateSuggestions.style.display = 'none';
      suggestionState.delete(itemTemplateSuggestions);
      suggestionState.delete(groupTemplateSuggestions);
      suggestionState.delete(glanceTemplateSuggestions);
    }}

    function hideEntitySuggestions() {{
      entitySuggestions.style.display = 'none';
      suggestionState.delete(entitySuggestions);
    }}

    function setActiveSuggestion(box, index, selector = '.template-suggestion') {{
      const buttons = Array.from(box.querySelectorAll(selector));
      if (buttons.length === 0) return;
      const nextIndex = (index + buttons.length) % buttons.length;
      buttons.forEach((button, buttonIndex) => {{
        button.classList.toggle('active', buttonIndex === nextIndex);
      }});
      buttons[nextIndex].scrollIntoView({{ block: 'nearest' }});
      suggestionState.set(box, {{ index: nextIndex }});
    }}

    function acceptActiveSuggestion(input, box) {{
      const buttons = Array.from(box.querySelectorAll('.template-suggestion'));
      if (buttons.length === 0 || box.style.display === 'none') return false;
      const state = suggestionState.get(box) || {{ index: 0 }};
      const button = buttons[state.index] || buttons[0];
      applyTemplateSuggestion(input, button.dataset.entityId);
      return true;
    }}

    function handleTemplateSuggestionKeys(event, input, box) {{
      const visible = box.style.display !== 'none';
      if (!visible && ['ArrowDown', 'ArrowUp'].includes(event.key)) {{
        renderTemplateSuggestions(input, box);
      }}
      if (event.key === 'ArrowDown') {{
        event.preventDefault();
        const state = suggestionState.get(box) || {{ index: -1 }};
        setActiveSuggestion(box, state.index + 1);
      }} else if (event.key === 'ArrowUp') {{
        event.preventDefault();
        const state = suggestionState.get(box) || {{ index: 0 }};
        setActiveSuggestion(box, state.index - 1);
      }} else if (event.key === 'Enter' && visible) {{
        if (acceptActiveSuggestion(input, box)) event.preventDefault();
      }} else if (event.key === 'Escape') {{
        hideTemplateSuggestions();
      }}
    }}

    function renderTemplateSuggestions(input, box) {{
      const tokenInfo = tokenAtCursor(input);
      const token = tokenInfo.token.toLowerCase();
      const selected = entityPicker.value.trim();
      const matches = entities
        .filter((entity) => {{
          if (!token && selected) return entity.entity_id === selected;
          if (token.length < 2) return false;
          return entity.entity_id.toLowerCase().includes(token) || entity.name.toLowerCase().includes(token);
        }})
        .slice(0, 30);

      box.innerHTML = '';
      if (matches.length === 0) {{
        box.style.display = 'none';
        return;
      }}

      for (const entity of matches) {{
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'template-suggestion';
        button.dataset.entityId = entity.entity_id;
        button.innerHTML = escapeHtml(entity.entity_id) + '<small>' + escapeHtml(entity.name + ' - ' + entity.domain) + '</small>';
        button.addEventListener('mousedown', (event) => {{
          event.preventDefault();
          applyTemplateSuggestion(input, entity.entity_id);
        }});
        box.appendChild(button);
      }}
      box.style.display = 'block';
      setActiveSuggestion(box, 0);
    }}

    function applyEntitySuggestion(entityId) {{
      entityPicker.value = entityId;
      hideEntitySuggestions();
      entityPicker.dispatchEvent(new Event('change'));
    }}

    function renderEntitySuggestions() {{
      const query = entityPicker.value.trim().toLowerCase();
      const matches = entities
        .filter((entity) => {{
          if (!query) return true;
          return entity.entity_id.toLowerCase().includes(query)
            || entity.name.toLowerCase().includes(query)
            || entity.domain.toLowerCase().includes(query)
            || entityTypeLabel(entity).toLowerCase().includes(query)
            || (entity.area || '').toLowerCase().includes(query);
        }})
        .sort((left, right) => {{
          const leftName = left.name.toLowerCase();
          const rightName = right.name.toLowerCase();
          const leftId = left.entity_id.toLowerCase();
          const rightId = right.entity_id.toLowerCase();
          const score = (entity) => {{
            const name = entity.name.toLowerCase();
            const entityId = entity.entity_id.toLowerCase();
            const area = (entity.area || '').toLowerCase();
            if (!query) return 10;
            if (name === query || entityId === query) return 0;
            if (name.startsWith(query)) return 1;
            if (area.startsWith(query)) return 2;
            if (entityId.startsWith(query)) return 3;
            if (name.includes(query)) return 4;
            if (area.includes(query)) return 5;
            if (entityId.includes(query)) return 6;
            return 7;
          }};
          const scoreDiff = score(left) - score(right);
          if (scoreDiff !== 0) return scoreDiff;
          return leftName.localeCompare(rightName) || leftId.localeCompare(rightId);
        }})
        .slice(0, 30);

      entitySuggestions.innerHTML = '';
      if (matches.length === 0) {{
        hideEntitySuggestions();
        return;
      }}

      for (const entity of matches) {{
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'entity-suggestion';
        button.dataset.entityId = entity.entity_id;
        const areaText = entity.area || 'Home Assistant';
        button.innerHTML =
          '<div class="entity-icon">' + escapeHtml(entityIcon(entity)) + '</div>' +
          '<div><div class="entity-name">' + escapeHtml(entity.name) + '</div>' +
          '<div class="entity-sub">' + escapeHtml(areaText + ' - ' + entity.entity_id) + '</div></div>' +
          '<div class="entity-domain">' + escapeHtml(entityTypeLabel(entity)) + '</div>';
        button.addEventListener('mousedown', (event) => {{
          event.preventDefault();
          applyEntitySuggestion(entity.entity_id);
        }});
        entitySuggestions.appendChild(button);
      }}
      entitySuggestions.style.display = 'block';
      setActiveSuggestion(entitySuggestions, 0, '.entity-suggestion');
    }}

    function acceptActiveEntitySuggestion() {{
      const buttons = Array.from(entitySuggestions.querySelectorAll('.entity-suggestion'));
      if (buttons.length === 0 || entitySuggestions.style.display === 'none') return false;
      const state = suggestionState.get(entitySuggestions) || {{ index: 0 }};
      const button = buttons[state.index] || buttons[0];
      applyEntitySuggestion(button.dataset.entityId);
      return true;
    }}

    function handleEntitySuggestionKeys(event) {{
      const visible = entitySuggestions.style.display !== 'none';
      if (!visible && ['ArrowDown', 'ArrowUp'].includes(event.key)) {{
        renderEntitySuggestions();
      }}
      if (event.key === 'ArrowDown') {{
        event.preventDefault();
        const state = suggestionState.get(entitySuggestions) || {{ index: -1 }};
        setActiveSuggestion(entitySuggestions, state.index + 1, '.entity-suggestion');
      }} else if (event.key === 'ArrowUp') {{
        event.preventDefault();
        const state = suggestionState.get(entitySuggestions) || {{ index: 0 }};
        setActiveSuggestion(entitySuggestions, state.index - 1, '.entity-suggestion');
      }} else if (event.key === 'Enter' && visible) {{
        if (acceptActiveEntitySuggestion()) event.preventDefault();
      }} else if (event.key === 'Escape') {{
        hideEntitySuggestions();
      }}
    }}

    function selectedEntityStateTemplate() {{
      const entityId = entityPicker.value.trim();
      if (!entityId) return '';
      return "{{{{ states('" + entityId + "') }}}}";
    }}

    function rememberCaret(input) {{
      if (!input) return;
      const start = typeof input.selectionStart === 'number' ? input.selectionStart : input.value.length;
      const end = typeof input.selectionEnd === 'number' ? input.selectionEnd : start;
      caretPositions.set(input, {{ start, end }});
    }}

    function insertAtCursor(input, text) {{
      const remembered = caretPositions.get(input);
      const liveSelection = document.activeElement === input && typeof input.selectionStart === 'number';
      const start = liveSelection ? input.selectionStart : (remembered ? remembered.start : input.value.length);
      const end = liveSelection ? input.selectionEnd : (remembered ? remembered.end : start);
      input.value = input.value.slice(0, start) + text + input.value.slice(end);
      input.focus();
      input.selectionStart = input.selectionEnd = start + text.length;
      rememberCaret(input);
      updateWatchPreview();
      if (input === itemContent) scheduleItemTemplatePreview();
      if (input === groupContent) scheduleGroupTemplatePreview();
      if (input === glanceContent) updateGlanceJson(false);
    }}

    function typeIcon(type) {{
      if (type === 'toggle') return 'ON';
      if (type === 'tap') return 'GO';
      if (type === 'numeric') return '123';
      if (type === 'group') return 'MENU';
      return 'i';
    }}

    function updateWatchPreview() {{
      const meta = entityMeta(entityPicker.value.trim());
      watchPreviewIcon.textContent = meta ? entityIcon(meta) : typeIcon(itemType.value);
      watchPreviewTitle.textContent = itemName.value || 'Item preview';
      const rendered = itemTemplateResult.textContent.replace(/^Preview: /, '');
      const subtitle = rendered && rendered !== itemTemplateResult.textContent && !rendered.startsWith('Error:')
        ? rendered
        : itemContent.value;
      watchPreviewSubtitle.textContent = subtitle;
      watchPreviewSubtitle.hidden = !subtitle;
    }}

    function setupEmojiPickers() {{
      document.querySelectorAll('.emoji-grid[data-target]').forEach((row) => {{
        const picker = row.closest('.emoji-picker');
        const targetInput = document.getElementById(row.dataset.target);
        let activeTab = 'most';
        let panelTouchX = 0;
        let panelTouchY = 0;
        let panelSwiped = false;
        const search = document.createElement('input');
        search.type = 'search';
        search.className = 'emoji-search';
        search.placeholder = 'Search emoji';
        search.setAttribute('aria-label', 'Search emoji');
        const panel = document.createElement('div');
        panel.className = 'emoji-panel';
        const tabs = document.createElement('div');
        tabs.className = 'emoji-tabs';

        const setActiveTab = (tabId) => {{
          activeTab = tabId;
          search.value = '';
          renderEmojiButtons();
          const activeButton = tabs.querySelector('.emoji-tab.active');
          if (activeButton) activeButton.scrollIntoView({{ behavior: 'smooth', block: 'nearest', inline: 'center' }});
        }};

        const shiftEmojiTab = (direction) => {{
          const index = emojiTabs.findIndex(([tabId]) => tabId === activeTab);
          if (index < 0) return;
          const next = Math.max(0, Math.min(emojiTabs.length - 1, index + direction));
          if (next !== index) setActiveTab(emojiTabs[next][0]);
        }};

        for (const [tabId, label] of emojiTabs) {{
          const tabButton = document.createElement('button');
          tabButton.type = 'button';
          tabButton.className = 'emoji-tab';
          tabButton.textContent = label;
          tabButton.dataset.tab = tabId;
          bindButton(tabButton, () => {{
            setActiveTab(tabId);
            search.focus();
          }});
          tabs.appendChild(tabButton);
        }}

        picker.insertBefore(panel, row);
        panel.append(search, tabs, row);

        const renderEmojiButtons = () => {{
          const query = search.value.trim().toLowerCase();
          const matches = emojiLibrary.filter((entry) => {{
            const [emoji, name] = entry;
            if (!query) return emojiMatchesTab(entry, activeTab);
            return name.includes(query);
          }});
          tabs.querySelectorAll('.emoji-tab').forEach((button) => {{
            button.classList.toggle('active', button.dataset.tab === activeTab && !query);
          }});
          row.innerHTML = '';
          for (const [emoji, name] of matches) {{
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'emoji-button';
            button.textContent = emoji;
            button.title = name;
            button.setAttribute('aria-label', 'Insert ' + name);
            bindButton(button, () => {{
              insertAtCursor(targetInput, emoji + ' ');
              const openPicker = row.closest('.emoji-picker');
              if (openPicker) openPicker.classList.remove('open');
              search.value = '';
              renderEmojiButtons();
            }});
            row.appendChild(button);
          }}
          if (matches.length === 0) {{
            const empty = document.createElement('div');
            empty.className = 'help';
            empty.textContent = query ? 'No emoji found.' : 'No emoji in this category.';
            row.appendChild(empty);
          }}
        }};

        search.addEventListener('input', renderEmojiButtons);
        search.addEventListener('keydown', (event) => {{
          if (event.key === 'Escape') {{
            picker.classList.remove('open');
          }}
        }});
        panel.addEventListener('touchstart', (event) => {{
          const touch = event.changedTouches && event.changedTouches[0];
          if (!touch) return;
          panelTouchX = touch.clientX;
          panelTouchY = touch.clientY;
          panelSwiped = false;
        }}, {{ passive: true }});
        panel.addEventListener('touchmove', (event) => {{
          const touch = event.changedTouches && event.changedTouches[0];
          if (!touch) return;
          const deltaX = touch.clientX - panelTouchX;
          const deltaY = touch.clientY - panelTouchY;
          if (Math.abs(deltaX) > 42 && Math.abs(deltaY) < 55) {{
            shiftEmojiTab(deltaX < 0 ? 1 : -1);
            panelTouchX = touch.clientX;
            panelTouchY = touch.clientY;
            panelSwiped = true;
          }}
        }}, {{ passive: true }});
        panel.addEventListener('touchend', (event) => {{
          const touch = event.changedTouches && event.changedTouches[0];
          if (!touch || panelSwiped) return;
          const deltaX = touch.clientX - panelTouchX;
          const deltaY = touch.clientY - panelTouchY;
          if (Math.abs(deltaX) > 34 && Math.abs(deltaY) < 55) {{
            shiftEmojiTab(deltaX < 0 ? 1 : -1);
          }}
        }}, {{ passive: true }});
        renderEmojiButtons();
      }});
      document.querySelectorAll('.emoji-toggle').forEach((button) => {{
        bindButton(button, () => {{
          const picker = button.closest('.emoji-picker');
          const grid = picker ? picker.querySelector('.emoji-grid[data-target]') : null;
          const targetInput = grid ? document.getElementById(grid.dataset.target) : null;
          rememberCaret(targetInput);
          const shouldOpen = !picker.classList.contains('open');
          document.querySelectorAll('.emoji-picker.open').forEach((openPicker) => openPicker.classList.remove('open'));
          if (shouldOpen) {{
            picker.classList.add('open');
            const search = picker.querySelector('.emoji-search');
            if (search) setTimeout(() => search.focus(), 0);
          }}
        }});
      }});
      document.addEventListener('click', () => {{
        document.querySelectorAll('.emoji-picker.open').forEach((picker) => picker.classList.remove('open'));
      }});
      document.querySelectorAll('.emoji-picker').forEach((picker) => {{
        picker.addEventListener('click', (event) => event.stopPropagation());
      }});
    }}

    async function loadEntities() {{
      const response = await fetch('{GARMIN_HOMEASSISTANT_ENTITIES_PATH}');
      if (!response.ok) return;
      entities = (await response.json()).entities || [];
      entityList.innerHTML = '';
      for (const entity of entities) {{
        const option = document.createElement('option');
        option.value = entity.entity_id;
        option.label = entity.name + ' (' + entity.domain + ')';
        entityList.appendChild(option);
      }}
    }}

    async function previewTemplate(templateText, output) {{
      const text = templateText.trim();
      if (!text) {{
        output.textContent = '';
        return;
      }}
      let parsed;
      try {{
        parsed = readDashboard();
      }} catch (err) {{
        output.textContent = 'Fix JSON before previewing.';
        return;
      }}
      const response = await fetch('{GARMIN_HOMEASSISTANT_TEMPLATE_PREVIEW_PATH}', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          setup_code: parsed.setup_code,
          template: text,
        }}),
      }});
      const body = await response.json();
      if (!response.ok) {{
        output.textContent = 'Error: ' + (body.message || response.status);
        return;
      }}
      output.textContent = 'Preview: ' + body.result;
    }}

    function scheduleItemTemplatePreview() {{
      clearTimeout(itemPreviewTimer);
      itemTemplateResult.textContent = itemContent.value.trim() ? 'Previewing...' : '';
      itemPreviewTimer = setTimeout(async () => {{
        const requestId = ++itemPreviewRequest;
        await previewTemplate(itemContent.value, itemTemplateResult);
        if (requestId === itemPreviewRequest) updateWatchPreview();
      }}, 450);
    }}

    function scheduleGroupTemplatePreview() {{
      clearTimeout(groupPreviewTimer);
      groupTemplateResult.textContent = groupContent.value.trim() ? 'Previewing...' : '';
      groupPreviewTimer = setTimeout(async () => {{
        ++groupPreviewRequest;
        await previewTemplate(groupContent.value, groupTemplateResult);
      }}, 450);
    }}

    entityPicker.addEventListener('change', () => {{
      const meta = entityMeta(entityPicker.value);
      if (!meta) return;
      if (!itemName.value) itemName.value = meta.name;
      if (itemType.value === 'auto') {{
        if (['light', 'switch', 'input_boolean'].includes(meta.domain)) itemType.value = 'toggle';
        else if (['automation', 'scene', 'script'].includes(meta.domain)) itemType.value = 'tap';
        else if (['input_number', 'number', 'fan', 'valve', 'cover', 'media_player', 'climate'].includes(meta.domain)) itemType.value = 'numeric';
        else itemType.value = 'info';
      }}
      updateBehaviorHelp();
      updateWatchPreview();
      scheduleItemTemplatePreview();
    }});
    entityPicker.addEventListener('input', renderEntitySuggestions);
    entityPicker.addEventListener('focus', renderEntitySuggestions);
    entityPicker.addEventListener('blur', () => setTimeout(hideEntitySuggestions, 150));
    entityPicker.addEventListener('keydown', handleEntitySuggestionKeys);

    itemName.addEventListener('input', updateWatchPreview);
    [itemName, itemContent, groupName, groupContent, glanceContent].forEach((input) => {{
      input.addEventListener('focus', () => rememberCaret(input));
      input.addEventListener('click', () => rememberCaret(input));
      input.addEventListener('keyup', () => rememberCaret(input));
      input.addEventListener('select', () => rememberCaret(input));
      input.addEventListener('input', () => rememberCaret(input));
    }});
    itemContent.addEventListener('input', () => {{
      updateWatchPreview();
      scheduleItemTemplatePreview();
      renderTemplateSuggestions(itemContent, itemTemplateSuggestions);
    }});
    itemContent.addEventListener('focus', () => renderTemplateSuggestions(itemContent, itemTemplateSuggestions));
    itemContent.addEventListener('blur', () => setTimeout(hideTemplateSuggestions, 150));
    itemContent.addEventListener('keyup', (event) => {{
      if (['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(event.key)) return;
      renderTemplateSuggestions(itemContent, itemTemplateSuggestions);
    }});
    itemContent.addEventListener('keydown', (event) => handleTemplateSuggestionKeys(event, itemContent, itemTemplateSuggestions));
    groupContent.addEventListener('input', () => {{
      scheduleGroupTemplatePreview();
      renderTemplateSuggestions(groupContent, groupTemplateSuggestions);
    }});
    groupContent.addEventListener('focus', () => renderTemplateSuggestions(groupContent, groupTemplateSuggestions));
    groupContent.addEventListener('blur', () => setTimeout(hideTemplateSuggestions, 150));
    groupContent.addEventListener('keyup', (event) => {{
      if (['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(event.key)) return;
      renderTemplateSuggestions(groupContent, groupTemplateSuggestions);
    }});
    groupContent.addEventListener('keydown', (event) => handleTemplateSuggestionKeys(event, groupContent, groupTemplateSuggestions));
    glanceContent.addEventListener('input', () => {{
      updateGlanceJson(false);
      renderTemplateSuggestions(glanceContent, glanceTemplateSuggestions);
    }});
    glanceContent.addEventListener('focus', () => renderTemplateSuggestions(glanceContent, glanceTemplateSuggestions));
    glanceContent.addEventListener('blur', () => setTimeout(hideTemplateSuggestions, 150));
    glanceContent.addEventListener('keyup', (event) => {{
      if (['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(event.key)) return;
      renderTemplateSuggestions(glanceContent, glanceTemplateSuggestions);
    }});
    glanceContent.addEventListener('keydown', (event) => handleTemplateSuggestionKeys(event, glanceContent, glanceTemplateSuggestions));
    glanceType.addEventListener('change', () => {{
      updateGlanceVisibility();
      updateGlanceJson(false);
    }});
    itemType.addEventListener('change', () => {{
      updateBehaviorHelp();
      updateWatchPreview();
    }});

    document.querySelectorAll('[data-copy]').forEach((button) => {{
      bindButton(button, async () => {{
        const input = document.getElementById(button.dataset.copy);
        input.select();
        const copied = await copyWithPanel(button.title || 'Copy value', input.value);
        setStatus(copied ? 'Copied. A selectable fallback is shown above.' : 'Copy fallback shown above.');
      }});
    }});

    document.querySelectorAll('[data-copy-url]').forEach((button) => {{
      bindButton(button, async () => {{
        const url = button.dataset.copyUrl.startsWith('/')
          ? window.location.origin + button.dataset.copyUrl
          : button.dataset.copyUrl;
        const copied = await copyWithPanel(button.textContent, url);
        setStatus(copied ? 'Link copied. A selectable fallback is shown above.' : 'Copy fallback shown above.');
      }});
    }});

    document.querySelectorAll('[data-open-url]').forEach((button) => {{
      bindButton(button, () => {{
        const url = button.dataset.openUrl;
        setStatus('Opening link...');
        try {{
          if (window.top && window.top !== window) {{
            window.top.location.assign(url);
          }} else {{
            window.location.assign(url);
          }}
          window.setTimeout(() => {{
            if (document.visibilityState === 'visible') {{
              showCopyPanel(button.textContent, url, false);
              setStatus('If the link did not open, use the copy fallback above.', true);
            }}
          }}, 1200);
        }} catch (err) {{
          showCopyPanel(button.textContent, url, false);
          setStatus('Open link failed. Use the copy fallback above.', true);
        }}
      }});
    }});

    bindButton(document.getElementById('copy-panel-close'), () => {{
      copyPanel.hidden = true;
    }});

    bindButton(copyPanelCopy, async () => {{
      try {{
        await copyText(copyPanelValue.value);
        copyPanel.hidden = true;
        setStatus('Copied.');
      }} catch (err) {{
        copyPanelValue.focus();
        copyPanelValue.select();
        setStatus('Copy failed. Press Ctrl+C to copy the selected value.', true);
      }}
    }});

    bindButton(document.getElementById('update-base-url'), () => {{
      try {{
        const parsed = readDashboard();
        parsed.base_url = cleanBaseUrl();
        writeDashboard(parsed);
        setStatus('Base URL updated. Save dashboard to publish it.', false, 'json');
      }} catch (err) {{
        setStatus('Base URL update failed: ' + err.message, true, 'json');
      }}
    }});

    bindButton(document.getElementById('update-glance'), async () => {{
      updateGlanceJson(false);
      await saveDashboard('glance', 'Glance updated and dashboard saved.');
    }});

    bindButton(document.getElementById('rotate-code'), () => {{
      try {{
        const parsed = readDashboard();
        if (!confirm('Rotate the configuration key? You will need to update the Configuration URL in GarminHomeAssistant.')) return;
        parsed.setup_code = slugId('CFG').replace(/_/g, '').slice(0, 8);
        writeDashboard(parsed);
        setStatus('Configuration key rotated. Save dashboard, then update GarminHomeAssistant settings.', false, 'json');
      }} catch (err) {{
        setStatus('Rotate failed: ' + err.message, true, 'json');
      }}
    }});

    bindButton(document.getElementById('insert-item-state'), () => {{
      const snippet = selectedEntityStateTemplate();
      if (!snippet) {{
        setStatus('Choose an entity first.', true, 'item');
        return;
      }}
      insertAtCursor(itemContent, snippet);
    }});

    bindButton(cancelEditItemButton, resetItemForm);
    bindButton(cancelEditGroupButton, resetGroupForm);
    bindButton(addItemButton, () => {{
      try {{
        const parsed = readDashboard();
        const entityId = entityPicker.value.trim();
        if (!entityId && itemType.value !== 'tap') throw new Error('Choose an entity first');
        const meta = entityMeta(entityId);
        if (!entityId && !itemAction.value.trim()) throw new Error('Enter a custom action when no entity is selected');
        const name = itemName.value.trim() || (meta && meta.name) || entityId || itemAction.value.trim();
        const actionData = actionDataWithNumericOptions(validateActionData());
        const values = {{
          type: itemType.value,
          entity_id: entityId,
          name,
          content: itemContent.value.trim(),
          title: name,
          tap_action_action: itemAction.value.trim(),
          tap_action_data: actionData,
          confirm: confirmValue(),
          pin: itemPin.checked,
          exit: itemExit.checked,
          enabled: itemEnabled.checked,
          numeric_min: optionalNumber(numericMin),
          numeric_max: optionalNumber(numericMax),
          numeric_step: optionalNumber(numericStep),
          numeric_attribute: numericAttribute.value.trim(),
          numeric_data_attribute: numericDataAttribute.value.trim(),
        }};
        const wasEditing = Boolean(editingItemId);
        if (editingItemId) {{
          updateExistingItem(parsed, editingItemId, values);
        }} else {{
          addToParent(parsed, parentGroup.value, {{
            id: slugId(name),
            ...values,
            items: [],
          }});
        }}
        writeDashboard(parsed);
        resetItemForm();
        setStatus(wasEditing ? 'Item updated. Save dashboard to publish it.' : 'Item added. Save dashboard to publish it.', false, 'item');
      }} catch (err) {{
        setStatus((editingItemId ? 'Update item failed: ' : 'Add item failed: ') + err.message, true, 'item');
      }}
    }});

    bindButton(addGroupButton, () => {{
      try {{
        const parsed = readDashboard();
        const name = groupName.value.trim();
        if (!name) throw new Error('Enter a submenu name');
        const values = {{
          type: 'group',
          entity_id: '',
          name,
          title: groupTitle.value.trim() || name,
          content: groupContent.value.trim(),
          confirm: false,
          pin: false,
          exit: false,
          enabled: groupEnabled.checked,
        }};
        const wasEditing = Boolean(editingGroupId);
        if (editingGroupId) {{
          updateExistingGroup(parsed, editingGroupId, values);
        }} else {{
          addToParent(parsed, groupParent.value, {{
            id: slugId(name),
            ...values,
            items: [],
          }});
        }}
        writeDashboard(parsed);
        resetGroupForm();
        setStatus(wasEditing ? 'Submenu updated. Save dashboard to publish it.' : 'Submenu added. Save dashboard to publish it.', false, 'group');
      }} catch (err) {{
        setStatus((editingGroupId ? 'Update submenu failed: ' : 'Add submenu failed: ') + err.message, true, 'group');
      }}
    }});

    bindButton(document.getElementById('format'), () => {{
      try {{
        writeDashboard(JSON.parse(dashboard.value));
        setStatus('JSON formatted.', false, 'json');
      }} catch (err) {{
        setStatus('Invalid JSON: ' + err.message, true, 'json');
      }}
    }});

    jsonHighlight.addEventListener('input', () => {{
      syncDashboardFromEditor();
      updateUnsavedBar();
    }});
    jsonHighlight.addEventListener('blur', () => {{
      syncDashboardFromEditor();
      updateJsonHighlight();
      updateUnsavedBar();
    }});
    dashboard.addEventListener('input', () => {{
      updateJsonHighlight();
      updateUnsavedBar();
    }});

    bindButton(document.getElementById('copy-dashboard-json'), async () => {{
      syncDashboardFromEditor();
      const copied = await copyWithPanel('Dashboard JSON', dashboard.value);
      setStatus(copied ? 'Dashboard JSON copied. Fallback shown above.' : 'Copy fallback shown above.', false, 'json');
    }});

    bindButton(document.getElementById('copy-config-url'), async () => {{
      const copied = await copyWithPanel('Garmin JSON URL', configUrl.value);
      setStatus(copied ? 'Garmin JSON URL copied. Fallback shown above.' : 'Copy fallback shown above.', false, 'json');
    }});

    bindButton(document.getElementById('view-config-url'), () => {{
      try {{
        window.location.href = localConfigUrl();
      }} catch (err) {{
        setStatus('Open Garmin JSON failed: ' + err.message, true, 'json');
      }}
    }});

    bindButton(document.getElementById('save'), () => saveDashboard('save', 'Dashboard saved.'));
    bindButton(unsavedSave, () => saveDashboard('save', 'Dashboard saved.'));
    bindButton(document.getElementById('reload-dashboard'), async () => {{
      const response = await fetch('{GARMIN_HOMEASSISTANT_DASHBOARD_PATH}');
      if (!response.ok) {{
        setStatus('Reload failed: HTTP ' + response.status, true, 'save');
        return;
      }}
      const latest = await response.json();
      suppressDirtyState = true;
      writeDashboard(latest);
      suppressDirtyState = false;
      lastSavedDashboard = dashboard.value;
      staleWarning.classList.remove('visible');
      updateUnsavedBar();
      setStatus('Reloaded latest dashboard.', false, 'save');
    }});
    bindButton(unsavedReload, async () => {{
      const response = await fetch('{GARMIN_HOMEASSISTANT_DASHBOARD_PATH}');
      if (!response.ok) {{
        setStatus('Discard failed: HTTP ' + response.status, true, 'save');
        return;
      }}
      const latest = await response.json();
      suppressDirtyState = true;
      writeDashboard(latest);
      suppressDirtyState = false;
      lastSavedDashboard = dashboard.value;
      staleWarning.classList.remove('visible');
      updateUnsavedBar();
      setStatus('Discarded unsaved changes.', false, 'save');
    }});

    async function checkForRemoteChanges() {{
      if (dashboard.value !== lastSavedDashboard) return;
      const response = await fetch('{GARMIN_HOMEASSISTANT_DASHBOARD_PATH}');
      if (!response.ok) return;
      const latest = await response.json();
      const latestText = JSON.stringify(latest, null, 2);
      if (latestText !== lastSavedDashboard) {{
        staleWarning.classList.add('visible');
      }}
    }}

    setInterval(checkForRemoteChanges, 15000);
    syncGlanceControls(initialDashboard);
    refreshGroupOptions();
    refreshSetupUrls();
    renderItems();
    updateJsonHighlight();
    setupEmojiPickers();
    updateBehaviorHelp();
    updateWatchPreview();
    updateUnsavedBar();
    loadEntities();
  </script>
</body>
</html>"""


