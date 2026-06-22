# Home Assistant for Garmin

`homeassistant-garmin` is a Home Assistant custom integration that helps you
build menus for the open-source
[GarminHomeAssistant Connect IQ application](https://apps.garmin.com/en-US/apps/61c91d28-ec5e-438d-9f83-39e9f45b199d)
by [house-of-abbey](https://github.com/house-of-abbey/GarminHomeAssistant).

GarminHomeAssistant is the watch app. This project is the Home Assistant
companion builder for it.

> Made for GarminHomeAssistant by house-of-abbey.
> This project is not affiliated with, endorsed by, or official to
> GarminHomeAssistant unless it is accepted upstream by that project.

## What This Project Does

Home Assistant for Garmin adds a **Garmin** page to the Home Assistant sidebar.
From that page you can:

- choose Home Assistant entities with a beginner-friendly UI
- build the GarminHomeAssistant menu without hand-writing JSON
- add info rows, toggles, run-action rows, numeric pickers, and submenus
- reorder, edit, and remove menu items
- add template text and emoji for watch labels
- generate the API URL and Configuration URL expected by GarminHomeAssistant
- copy setup values from desktop or the Home Assistant mobile app
- inspect and copy the generated JSON when you need advanced control

This repository does **not** include a separate Garmin widget, glance, watch
face, or Connect IQ app. Install GarminHomeAssistant from Garmin Connect IQ and
use this integration to configure it.

## Beginner Install Flow

### 1. Install GarminHomeAssistant On The Watch

Install the GarminHomeAssistant app from Garmin Connect IQ:

[GarminHomeAssistant app listing](https://apps.garmin.com/en-US/apps/61c91d28-ec5e-438d-9f83-39e9f45b199d)

You will configure its app settings from Garmin Connect / Connect IQ on your
phone after the Home Assistant integration is ready.

### 2. Install This Integration With HACS

Until this is available as a default HACS repository, add it as a custom
repository:

1. Open **HACS** in Home Assistant.
2. Open the three-dot menu.
3. Select **Custom repositories**.
4. Repository: `https://github.com/StumblingGamer/homeassistant-garmin`
5. Category: **Integration**.
6. Select **Add**.
7. Install **Home Assistant for Garmin**.
8. Restart Home Assistant.

### 3. Add The Integration In Home Assistant

1. Go to **Settings > Devices & services**.
2. Select **Add integration**.
3. Search for **Home Assistant for Garmin**.
4. Add it.
5. Open **Garmin** from the Home Assistant sidebar.

### 4. Copy Values Into GarminHomeAssistant

In the sidebar builder, open **Watch App Settings**.

Copy these values into GarminHomeAssistant settings in Garmin Connect / Connect
IQ on your phone:

| GarminHomeAssistant setting | What to paste |
| --- | --- |
| API URL | The builder's API URL |
| Configuration URL | The builder's Configuration URL |
| API key | A Home Assistant long-lived access token |

### 5. Build Your First Menu Item

1. In **Add Item**, choose a simple entity such as a light, switch, or sensor.
2. Let **Name on watch** auto-fill, or edit it.
3. Leave **Behavior** on **Automatic** for the first test.
4. Select **Add item**.
5. Select **Save dashboard** in the sticky save bar.
6. Open GarminHomeAssistant on the watch.

## Manual Install

If you are not using HACS, copy this folder from the repository:

```text
custom_components/homeassistant_garmin
```

Into your Home Assistant config folder as:

```text
custom_components/homeassistant_garmin
```

Restart Home Assistant, then add the integration from
**Settings > Devices & services > Add integration**.

## Security And Long-Lived Tokens

GarminHomeAssistant uses a Home Assistant long-lived access token as its API key.
This is how the watch app authenticates with Home Assistant.

Important points:

- Treat the token like a password.
- Home Assistant only shows the token once.
- Create a dedicated token named something like `GarminHomeAssistant`.
- Paste the token only into the GarminHomeAssistant app settings.
- If the token is exposed, delete it from your Home Assistant user profile and
  create a new one.
- Use HTTPS for remote access whenever possible.

This builder does not need to generate or store your long-lived access token.
It shows instructions for creating one, then helps you copy the URLs that go
beside it in the GarminHomeAssistant settings.

## Home Assistant URL

GarminHomeAssistant communicates through your phone, so the URL must be
reachable from the phone.

Common secure options:

- Home Assistant Cloud / Nabu Casa, which is the easiest paid option
- your own HTTPS reverse proxy
- Cloudflare Tunnel or a similar tunnel
- VPN, if your phone is connected to it while using the app

When Nabu Casa is available, the builder tries to use that URL automatically. If
not, enter your own external Home Assistant URL in **Watch App Settings**.

## Mobile Home Assistant App

The builder is intended to work from both desktop Home Assistant and the Home
Assistant mobile app.

Useful mobile flow:

1. Open Home Assistant on your phone.
2. Open **Garmin** from the sidebar.
3. Open **Watch App Settings**.
4. Copy the API URL and Configuration URL.
5. Paste them into GarminHomeAssistant settings in Garmin Connect / Connect IQ.

Some phones or embedded web views block direct external links. When that happens,
use the copy buttons and paste the link into your browser or Garmin app.

## Screenshots

Screenshots are tracked in [docs/screenshots](docs/screenshots/README.md).
Current recommended screenshots:

- Watch App Settings
- Add Item with entity picker
- Number picker setup
- Menu Items hierarchy
- Garmin JSON preview

## Documentation

- [Getting Started](docs/getting-started.md)
- [Dashboard Builder](docs/dashboard-builder.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Screenshots](docs/screenshots/README.md)

## HACS Release Packaging

This repository uses the standard custom integration layout:

```text
custom_components/homeassistant_garmin
```

To create a release zip for HACS:

```powershell
.\scripts\package-hacs.ps1
```

The release zip should contain `custom_components/homeassistant_garmin` at the
archive root.

Recommended GitHub/HACS topics:

```text
home-assistant
garmin
connect-iq
```

## Quick Troubleshooting

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

Use the builder's JSON preview to inspect the generated GarminHomeAssistant
configuration, then adjust the item behavior or advanced fields.
