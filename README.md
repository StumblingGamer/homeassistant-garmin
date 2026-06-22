# Home Assistant for Garmin

`homeassistant-garmin` is a Home Assistant custom integration that acts as a
companion builder for the open-source
[GarminHomeAssistant Connect IQ application](https://apps.garmin.com/en-US/apps/61c91d28-ec5e-438d-9f83-39e9f45b199d)
by house-of-abbey.

GarminHomeAssistant provides the watch app. This integration provides the Home
Assistant-side setup experience: choose entities, build the watch menu, generate
the GarminHomeAssistant JSON configuration, and copy the URLs needed in the
Connect IQ app settings.

## What This Project Does

Home Assistant for Garmin gives you a **Garmin** sidebar page in Home Assistant
where you can:

- build a GarminHomeAssistant menu without hand-writing JSON
- add Home Assistant entities as watch menu items
- create submenus for rooms, areas, or control groups
- configure common GarminHomeAssistant item types: info, toggle, run action,
  numeric picker, and submenu
- add glance text
- reorder, edit, and remove menu items
- use templates and emoji in watch labels and secondary text
- copy the GarminHomeAssistant API URL and Configuration URL
- save the generated dashboard configuration from Home Assistant

The watch app still uses the standard GarminHomeAssistant authentication model:
you create a Home Assistant long-lived access token and paste it into the
GarminHomeAssistant app settings on your phone.

## What You Need

1. Home Assistant.
2. This custom integration installed under `custom_components/homeassistant_garmin`.
3. The GarminHomeAssistant Connect IQ app installed on your watch through Garmin
   Connect IQ.
4. A Home Assistant URL your phone can reach.
5. A Home Assistant long-lived access token.

For many users, the easiest reachable URL is Home Assistant Cloud / Nabu Casa.
That is a paid secure remote-access option. You can also use your own HTTPS
reverse proxy, Cloudflare Tunnel, VPN, or another secure external access method
if it works from the phone running Garmin Connect.

## Configure GarminHomeAssistant

In the Home Assistant sidebar builder, open **Watch App Settings**.

Copy these values into the GarminHomeAssistant settings in Garmin Connect IQ:

| GarminHomeAssistant setting | What to paste |
| --- | --- |
| API URL | The builder's API URL |
| Configuration URL | The builder's Configuration URL |
| API key | A Home Assistant long-lived access token |

Create the long-lived token in Home Assistant from your user profile. Home
Assistant only shows the token once, so copy it immediately and store it
somewhere safe if needed.

## Build Your Watch Menu

Start simple:

1. In **Add Item**, choose an entity.
2. Let **Name on watch** auto-fill, or edit it.
3. Leave **Behavior** on **Automatic** for the first test.
4. Leave **Secondary text template** blank unless you want a second line.
5. Select **Add item**.
6. Select **Save dashboard**.
7. Open GarminHomeAssistant on the watch.

Once that works, add more items, submenus, custom text, numeric pickers, and
actions.

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
from your phone. If Nabu Casa is enabled, the builder should prefer that URL.

**Actions do nothing**

Confirm the long-lived access token is pasted into GarminHomeAssistant's API key
setting and has not been revoked.

**The generated menu looks wrong**

Use the builder's JSON preview to inspect the generated GarminHomeAssistant
configuration, then adjust the item behavior or advanced fields.
