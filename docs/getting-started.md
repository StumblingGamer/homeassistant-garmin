# Getting Started

Home Assistant for Garmin is the Home Assistant companion builder for the
[GarminHomeAssistant Connect IQ app](https://apps.garmin.com/en-US/apps/61c91d28-ec5e-438d-9f83-39e9f45b199d).

The watch app runs on your Garmin device. This integration runs inside Home
Assistant and helps you build the menu that the watch app displays.

This project is made for GarminHomeAssistant by house-of-abbey, but it is not
affiliated with, endorsed by, or official to GarminHomeAssistant unless accepted
upstream by that project.

This guide is written for a first-time setup.

## The Big Picture

There are three pieces:

1. **Home Assistant for Garmin**: the custom integration and sidebar builder.
2. **GarminHomeAssistant**: the Connect IQ app installed on the watch.
3. **Garmin Connect / Connect IQ on your phone**: where you paste the app
   settings.

The builder generates two URLs for GarminHomeAssistant:

- **API URL**: where the app sends normal Home Assistant API requests.
- **Configuration URL**: where the app downloads the watch menu JSON.

GarminHomeAssistant also needs an **API key**. In Home Assistant terms, that is
a long-lived access token from your user profile.

The useful mental model:

- The watch app is the remote control.
- The phone is usually the network bridge.
- Home Assistant for Garmin is the menu/configuration builder.
- GarminHomeAssistant reads the saved menu from the Configuration URL.

## Step 1: Install The Home Assistant Integration With HACS

Until Home Assistant for Garmin is available as a default HACS repository, add
it as a custom repository:

1. Open **HACS** in Home Assistant.
2. Open the three-dot menu.
3. Select **Custom repositories**.
4. Repository: `https://github.com/StumblingGamer/homeassistant-garmin`
5. Category: **Integration**.
6. Select **Add**.
7. Install **Home Assistant for Garmin**.
8. Restart Home Assistant.

After restart, go to:

```text
Settings > Devices & services > Add integration
```

Search for **Home Assistant for Garmin** and add it.

After the integration loads, open **Garmin** from the Home Assistant sidebar.

## Manual Install Fallback

If you are not using HACS, copy this folder from the repository:

Copy:

```text
custom_components/homeassistant_garmin
```

to:

```text
custom_components/homeassistant_garmin
```

Restart Home Assistant.

Then go to:

```text
Settings > Devices & services > Add integration
```

Search for **Home Assistant for Garmin** and add it.

After the integration loads, open **Garmin** from the Home Assistant sidebar.

If the sidebar item does not appear:

1. Hard refresh the Home Assistant browser/app.
2. Confirm the integration was added under **Settings > Devices & services**.
3. Restart Home Assistant again if you copied files while Home Assistant was
   already running.

## Step 2: Install GarminHomeAssistant

Install GarminHomeAssistant from the Garmin Connect IQ store:

```text
https://apps.garmin.com/en-US/apps/61c91d28-ec5e-438d-9f83-39e9f45b199d
```

You configure the app from Garmin Connect / Connect IQ on your phone. The exact
screen varies by phone and Garmin app version, but you are looking for the app's
settings page.

The settings you eventually paste are:

- API URL
- Configuration URL
- API key

Do not guess those values. Let the Home Assistant builder generate the URLs.

## Step 3: Choose A Reachable Home Assistant URL

GarminHomeAssistant communicates through your phone. That means the URL must be
reachable from the phone when the watch app runs.

Common options:

- **Home Assistant Cloud / Nabu Casa**: easiest secure option, paid.
- **Your own HTTPS reverse proxy**: works if it uses a publicly trusted
  certificate and is reachable from your phone.
- **Cloudflare Tunnel or similar**: can work when configured correctly.
- **VPN**: can work if the phone is connected to the VPN when using the watch
  app.

The builder tries to use your Nabu Casa URL automatically when Home Assistant
exposes it. If that is not available, enter your own external URL in **Watch App
Settings**.

Good URL examples:

```text
https://example.ui.nabu.casa
https://ha.yourdomain.com
```

Local URLs can work only when the phone can reach that exact network. They often
fail across VLANs, guest/IoT networks, cellular, or away from home:

```text
http://homeassistant.local:8123
http://192.168.1.20:8123
```

## Step 4: Copy The Watch App Settings

In Home Assistant, open:

```text
Garmin > Watch App Settings
```

Copy these into GarminHomeAssistant settings on your phone:

| GarminHomeAssistant setting | Value |
| --- | --- |
| API URL | Copy from the builder |
| Configuration URL | Copy from the builder |
| API key | A Home Assistant long-lived access token |

To create the token:

1. Open your Home Assistant user profile.
2. Find **Long-lived access tokens**.
3. Create a token named something like `GarminHomeAssistant`.
4. Copy it immediately.
5. Paste it into GarminHomeAssistant's API key setting.

Treat that token like a password. If you think it was exposed, delete it in Home
Assistant and create a new one.

## Step 5: Add Your First Item

Start with one simple entity.

Good first choices:

- a light
- a switch
- a sensor
- a script
- a scene

In the builder:

1. Go to **Add Item**.
2. Search for the entity.
3. Let **Name on watch** auto-fill, or change it.
4. Leave **Behavior** on **Automatic**.
5. Optionally add a **Watch row content template**.
6. Select **Add item**.
7. Select **Save dashboard**.

Open GarminHomeAssistant on the watch. You should see the item you added.

If it does not appear, go back to the builder and open **View Garmin JSON**. The
item should be present in the generated JSON. If it is present there but not on
the watch, reopen GarminHomeAssistant or resync the app settings from the phone.

## Item Behaviors

**Automatic**

Best starting point. The builder chooses the GarminHomeAssistant item type from
the entity domain.

**Toggle**

For lights, switches, input booleans, and similar on/off entities.

**Run action**

For scripts, scenes, automations, buttons, or custom Home Assistant services.
Use the custom action fields only when the automatic service is not what you
want.

**Info only**

Displays status or text without running an action. The **Watch row content
template** is the main value shown by an info item.

**Number picker**

Displays a number picker on the watch. Use this for brightness, volume, fan
percentage, cover position, thermostat temperature, or input_number helpers.

The fields shown under Number picker are **override fields**. They are not
required for normal light brightness. The builder already knows common defaults
for lights, fans, covers, media players, climate entities, and number helpers.

Example: dimming `light.living_room`

1. In **Add Item**, select `light.living_room`.
2. Set **Name on watch** to something like `Living Room`.
3. Set **Behavior** to **Number picker**.
4. Leave the number picker override fields blank for the first test.
5. Select **Add item**.
6. Select **Save dashboard**.

For a light, the builder generates these GarminHomeAssistant defaults:

| Field | Generated value |
| --- | --- |
| Action | `light.turn_on` |
| Read attribute | `brightness` |
| Set data attribute | `brightness` |
| Minimum | `0` |
| Maximum | `255` |
| Step | `5` |

Only fill in the override fields if you want to change those generated values.
For example, set Step to `10` if the watch picker feels too fine-grained.

Transition seconds is experimental for number picker items. Some
GarminHomeAssistant versions do not pass extra action data from numeric picker
items, so a transition value may be ignored even when the light itself supports
transitions.

What each override means:

- **Override minimum**: lowest value shown in the watch picker.
- **Override maximum**: highest value shown in the watch picker.
- **Override step**: how much each picker step changes the value.
- **Read attribute**: where GarminHomeAssistant reads the current value from.
- **Override set data attribute**: the Home Assistant service data key that gets
  the chosen value.

For a brightness light, both the read attribute and set data attribute are
`brightness`, so the builder fills that in automatically.

For an `input_number`, the current number is usually the entity state itself, so
the read attribute is blank and the set data attribute is usually `value`.

## Smooth Light Changes

GarminHomeAssistant sends a Home Assistant service call when you confirm the
number picker value. The watch app does not gradually animate the value itself.

For lights, Home Assistant supports a `transition` service field on many light
platforms. The builder can include a transition value, but GarminHomeAssistant's
numeric picker path may ignore extra action data depending on app version. If
that happens, the light changes abruptly even though the bulb supports
transition.

If the device or integration ignores `transition`, the change will still be
abrupt. That part is controlled by Home Assistant and the light platform, not by
the builder.

## Glance

The Glance section controls what GarminHomeAssistant shows in the glance area.

- **Show API status** uses the normal app status.
- **Show custom text** lets you enter a template for custom glance text.

After changing glance behavior, use **Update and save glance**.

## Watch Row Content Templates

GarminHomeAssistant calls the smaller text under a row name `content`. In this
builder, that field is labeled **Watch row content template**.

Content templates can use Home Assistant templates. For example:

```text
{{ states('sensor.outdoor_temperature') }} degrees
```

The builder includes:

- entity suggestions while typing templates
- an **Insert selected entity state** button
- a **Template helper** dropdown with common examples
- emoji picker buttons for names and content templates
- a preview row so you can see roughly how the item will look

Template helpers include common smart-home patterns such as friendly on/off
text, light brightness percentage, media volume percentage, battery percentage,
and amplifier dB display from a media player's `volume_level` attribute.

Content is required for info rows. It is optional for toggles, run actions,
number pickers, and submenus.

## Save Matters

Adding or editing an item updates the builder draft. GarminHomeAssistant reads
the saved dashboard configuration.

After building or changing menu items, select:

```text
Save dashboard
```

The builder may show local status messages such as "Item added" before the
dashboard is saved. That means the draft changed in the page. The watch app will
not receive the changed menu until the dashboard is saved.

## Beginner Checklist

Use this checklist if you are not sure what step you are on:

1. Home Assistant integration installed and visible in Devices & services.
2. Garmin sidebar item opens the builder.
3. GarminHomeAssistant installed on the watch.
4. API URL copied from the builder into the phone app settings.
5. Configuration URL copied from the builder into the phone app settings.
6. Long-lived access token copied into the phone app API key field.
7. At least one item added in the builder.
8. Dashboard saved.
9. GarminHomeAssistant reopened on the watch.

## Mobile App Checklist

Use this to confirm the setup works from the Home Assistant mobile app:

1. Open the Home Assistant mobile app.
2. Open **Garmin** from the sidebar.
3. Open **Watch App Settings**.
4. Copy the API URL.
5. Copy the Configuration URL.
6. Paste both values into GarminHomeAssistant settings in Garmin Connect /
   Connect IQ.
7. Add or edit one item from the mobile builder.
8. Select **Save dashboard**.
9. Reopen GarminHomeAssistant on the watch and confirm the item appears.

If an external app or documentation link does not open from the mobile app, use
the copy button and paste the URL into your phone browser.

## Troubleshooting

See [Troubleshooting](troubleshooting.md).
