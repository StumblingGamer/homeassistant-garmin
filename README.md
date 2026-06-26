# Home Assistant for Garmin

`homeassistant-garmin` is a Home Assistant custom integration that helps you
build menus for the open-source
[GarminHomeAssistant Connect IQ application](https://apps.garmin.com/en-US/apps/61c91d28-ec5e-438d-9f83-39e9f45b199d)
by [house-of-abbey](https://github.com/house-of-abbey/GarminHomeAssistant).

GarminHomeAssistant is the Garmin watch app. Home Assistant for Garmin is the
Home Assistant companion builder for that app.

> Made for GarminHomeAssistant by house-of-abbey.
> This project is not affiliated with, endorsed by, or official to
> GarminHomeAssistant unless it is accepted upstream by that project.

## What It Does

Home Assistant for Garmin adds a **Garmin** page to the Home Assistant sidebar.
Use it to:

- pick Home Assistant entities from a friendly UI
- build the GarminHomeAssistant watch menu without hand-writing JSON
- create info rows, toggles, action rows, number pickers, and submenus
- add watch row content templates with live preview
- use emoji and Home Assistant templates in watch labels
- reorder, edit, and remove menu items
- copy the API URL and Configuration URL required by GarminHomeAssistant

This repository does not include a separate Garmin watch app. Install
GarminHomeAssistant from Garmin Connect IQ.

## What You Need

1. Home Assistant.
2. HACS, or the ability to manually copy a custom integration.
3. The GarminHomeAssistant app installed on your Garmin watch.
4. A Home Assistant URL your phone can reach.
5. A Home Assistant long-lived access token.

For many users, Home Assistant Cloud / Nabu Casa is the easiest secure remote
URL. It is a paid option. You can also use your own HTTPS reverse proxy,
Cloudflare Tunnel, VPN, or another secure method if it works from the phone that
runs Garmin Connect / Connect IQ.

## Install With HACS

Until this repository is available as a default HACS repository, add it as a
custom repository:

1. Open **HACS** in Home Assistant.
2. Open the three-dot menu.
3. Select **Custom repositories**.
4. Repository: `https://github.com/StumblingGamer/homeassistant-garmin`
5. Category: **Integration**.
6. Select **Add**.
7. Install **Home Assistant for Garmin**.
8. Restart Home Assistant.

Then add the integration:

1. Go to **Settings > Devices & services**.
2. Select **Add integration**.
3. Search for **Home Assistant for Garmin**.
4. Add it.
5. Open **Garmin** from the Home Assistant sidebar.

## Manual Install

Copy this folder from the repository:

```text
custom_components/homeassistant_garmin
```

Into your Home Assistant config folder as:

```text
custom_components/homeassistant_garmin
```

Restart Home Assistant, then add the integration from
**Settings > Devices & services > Add integration**.

## Configure GarminHomeAssistant

In Home Assistant, open **Garmin** from the sidebar, then open
**Watch App Settings**.

Copy these values into GarminHomeAssistant settings in Garmin Connect / Connect
IQ on your phone:

| GarminHomeAssistant setting | What to paste |
| --- | --- |
| API URL | The builder's API URL |
| Configuration URL | The builder's Configuration URL |
| API key | A Home Assistant long-lived access token |

## Security Note

The GarminHomeAssistant API key is a Home Assistant long-lived access token.
Treat it like a password.

- Create a dedicated token named something like `GarminHomeAssistant`.
- Home Assistant only shows the token once.
- Paste the token only into GarminHomeAssistant settings.
- If the token is exposed, delete it from your Home Assistant profile and create
  a new one.
- Prefer HTTPS for any URL used away from home.

This builder does not need to generate or store your long-lived token.

## Build Your First Menu Item

Start simple:

1. In **Add Item**, choose a light, switch, sensor, script, or scene.
2. Let **Name on watch** auto-fill, or edit it.
3. Leave **Behavior** on **Automatic** for the first test.
4. Leave **Watch row content template** blank unless you want custom text.
5. Select **Add item**.
6. Select **Save dashboard**.
7. Open GarminHomeAssistant on the watch.

For sensors and info rows, the builder can provide a simple state template. For
more polished rows, use the template helper beside **Watch row content
template**.

## Mobile Setup

The builder is designed to work in the Home Assistant mobile app:

1. Open the Home Assistant mobile app.
2. Open **Garmin** from the sidebar.
3. Copy the API URL and Configuration URL.
4. Paste them into GarminHomeAssistant settings in Garmin Connect / Connect IQ.
5. Add or edit menu items.
6. Save the dashboard.

Some mobile web views block external links. If a link does not open, use the
copy button and paste the URL into your browser or Garmin app.

## Documentation

- [Getting Started](docs/getting-started.md)
- [Dashboard Builder](docs/dashboard-builder.md)
- [Troubleshooting](docs/troubleshooting.md)

## Troubleshooting Shortcuts

**The watch does not update**

Save the dashboard after changing items. GarminHomeAssistant reads the saved
Configuration URL.

**The app cannot connect**

Confirm the API URL and Configuration URL use a Home Assistant URL reachable
from your phone.

**Actions do nothing**

Confirm the long-lived access token is pasted into GarminHomeAssistant's API key
setting and has not been revoked.

**The generated menu looks wrong**

Use **View Garmin JSON** in the builder to inspect what GarminHomeAssistant will
read.
