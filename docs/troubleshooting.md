# Troubleshooting

Use this when GarminHomeAssistant does not show the menu, cannot connect, or an
item does not work as expected.

## First Checks

Before digging into details, confirm these basics:

1. The Home Assistant integration is installed and loaded.
2. The **Garmin** sidebar builder opens.
3. GarminHomeAssistant is installed on the watch.
4. The phone app settings contain the current API URL, Configuration URL, and
   API key.
5. The dashboard has at least one item.
6. The dashboard was saved after the last change.

Most problems are caused by one of these values being stale or unreachable.

## Watch Cannot Connect

Check the **API URL** first.

It should:

- end with `/api`
- use a URL reachable from the phone running Garmin Connect
- usually use HTTPS for remote access
- usually be your Nabu Casa URL or another external URL when away from home

Examples:

```text
https://example.ui.nabu.casa/api
https://ha.yourdomain.com/api
```

Local-only URLs may fail:

```text
http://homeassistant.local:8123/api
http://192.168.1.20:8123/api
```

Local URLs can fail if your phone is on cellular, guest Wi-Fi, an IoT VLAN, or
any network that cannot reach Home Assistant.

## Invalid API Key

GarminHomeAssistant's **API key** is a Home Assistant long-lived access token.

Create it from your Home Assistant user profile:

1. Open your Home Assistant user profile.
2. Scroll to **Long-lived access tokens**.
3. Create a token named something like `GarminHomeAssistant`.
4. Copy it immediately.
5. Paste it into GarminHomeAssistant's API key setting.

Home Assistant only shows the token once. If you lose it, create a new one and
update GarminHomeAssistant.

If actions used to work and then stopped, check whether the token was deleted,
revoked, copied with an extra space, or replaced in the phone app settings.

## Configuration URL Does Not Load

The Configuration URL should return JSON.

In the builder:

1. Open **Watch App Settings**.
2. Copy the Configuration URL.
3. Open it in a browser.

Expected result:

- You should see JSON.
- It should include an `items` array.
- Your saved menu items should appear in that JSON.

If it does not:

- Reopen the builder and copy the Configuration URL again.
- Confirm the Base URL is correct.
- Confirm the configuration key was not rotated after you copied the URL.
- Click **Save dashboard**.
- Restart Home Assistant after copying updated integration files.

## External Documentation Links Do Not Open

Some external sites refuse to load inside an embedded Home Assistant panel. If a
site says it "refused to connect" or shows `ERR_BLOCKED_BY_RESPONSE`, it means
the site blocked being displayed inside the frame.

The builder tries to open external app/documentation links in the top-level
browser/app view. If your Home Assistant mobile app or browser still blocks it,
use the fallback copy panel and paste the URL into your mobile browser.

## Item Is Missing On The Watch

In Home Assistant for Garmin:

1. Confirm the item exists in **Menu Items**.
2. Click **Save dashboard**.
3. Open **View Garmin JSON** and confirm the item is present.
4. Reopen GarminHomeAssistant on the watch.

GarminHomeAssistant may cache menu data, so reopening the app is often needed.

If the item is in the builder but not in Garmin JSON, the item may be invalid or
the dashboard may not be saved.

If the item is in Garmin JSON but not on the watch, the watch app may not have
refreshed the configuration yet.

## Action Fails

For lights and switches, try **Behavior: Automatic** first.

For scripts, scenes, and automations, use **Behavior: Run action**. If you need a
specific service, put it in **Custom action**, for example:

```text
script.a_script
```

If custom action data is needed, enter a JSON object in **Custom action data
JSON**:

```json
{"message": "Hello"}
```

Test the same action in Home Assistant Developer Tools before assuming the watch
is the problem.

## Number Picker Does Not Work

For common entity types, the builder creates numeric picker defaults.

For a light dimmer such as `light.living_room`:

1. Select the light entity.
2. Set **Behavior** to **Number picker**.
3. Leave the override fields blank.
4. Add the item.
5. Save the dashboard.

The generated picker uses:

```json
{
  "action": "light.turn_on",
  "picker": {
    "attribute": "brightness",
    "data_attribute": "brightness",
    "min": 0,
    "max": 255,
    "step": 5
  }
}
```

Use override fields only when the generated defaults are wrong.

Common override examples:

- Change **Override step** to `10` if brightness changes are too granular.
- Use **Override minimum** and **Override maximum** for a custom number range.
- Use **Read attribute** when the current value lives in an entity attribute.
- Use **Override set data attribute** when the Home Assistant service expects a
  different data key.

## Brightness Changes Are Abrupt

The watch app sends a Home Assistant service call when you confirm the selected
number. It does not continuously fade the light while you scroll the picker.

Home Assistant light services often support a `transition` value. The builder
can generate this action data when **Transition seconds** is set:

```json
{"transition": 2}
```

then many lights can fade over about two seconds. However, GarminHomeAssistant's
numeric picker path may ignore extra action data depending on app version. If
the same Hue bulb fades from Home Assistant Developer Tools but not from the
watch, this is likely an app-side limitation rather than a bulb limitation.

## Emoji Looks Wrong On The Watch

Garmin devices do not render every emoji the same way a phone does. If the watch
shows a box or missing character, replace that emoji with plain text or a simpler
symbol.

## Changes Do Not Save

Builder changes happen in the page first. Click **Save dashboard** to publish
them to GarminHomeAssistant.

If another browser or phone has the builder open, reload the builder before
making more changes.

If you add an item, see the status message, but do not save, the watch app will
still use the old saved configuration.
