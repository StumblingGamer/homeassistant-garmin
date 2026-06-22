# Dashboard Builder

The Dashboard Builder is the main Home Assistant interface for this project. It
creates GarminHomeAssistant-compatible menu JSON without requiring the user to
write JSON by hand.

Open it from the Home Assistant sidebar:

```text
Garmin
```

Direct URL:

```text
/api/homeassistant_garmin/builder
```

## Setup Values

The **Watch App Settings** section shows the values that go into the
GarminHomeAssistant Connect IQ app settings:

- **API URL**
- **Configuration URL**
- **API key**, which is a Home Assistant long-lived access token

The builder tries to choose the best base URL automatically. When Home Assistant
Cloud / Nabu Casa is available, that URL is preferred because it is usually the
easiest secure remote URL for beginners.

Users who do not use Nabu Casa can enter their own HTTPS URL in the Base URL
field and update the generated JSON.

## Glance

The Glance section controls the app's glance behavior.

- **Show API status** does not need extra text.
- **Show custom text** displays a template field.

The **Update and save glance** button updates the glance JSON and saves the
dashboard in one step.

## Add Item

Use **Add Item** for anything that should appear as a row on the watch.

Typical flow:

1. Pick an entity.
2. Confirm or edit the watch name.
3. Choose a behavior.
4. Add optional secondary text.
5. Select **Add item**.
6. Select **Save dashboard**.

### Behavior: Automatic

Automatic is best for beginners. The builder looks at the entity domain and
chooses a GarminHomeAssistant item type.

Examples:

- lights and switches become toggles
- scripts, scenes, and automations become run actions
- sensors become info items

### Behavior: Toggle

Toggle is for on/off entities such as:

- lights
- switches
- input booleans

### Behavior: Run Action

Run Action is for entities or services that should run when selected.

Good fits:

- scripts
- scenes
- automations
- buttons
- custom Home Assistant service calls

The custom action fields only appear when this behavior is selected. Leave them
blank unless you need to override what GarminHomeAssistant would normally infer.

### Behavior: Info Only

Info Only shows a row on the watch without running an action. Use the secondary
text template for status details.

### Behavior: Number Picker

Number Picker shows a numeric control on the watch.

Use it for values such as:

- light brightness
- media volume
- fan percentage
- cover position
- valve position
- thermostat temperature
- input_number helpers

When this behavior is selected, the number picker fields appear directly in the
form. For common entity types, the builder generates the picker configuration
for you. The fields in the form are overrides.

Example for dimming `light.living_room`:

| Builder field | What to use |
| --- | --- |
| Entity | `light.living_room` |
| Behavior | `Number picker` |
| Override minimum | leave blank |
| Override maximum | leave blank |
| Override step | leave blank, or `10` for larger jumps |
| Read attribute | leave blank |
| Override set data attribute | leave blank |
| Transition seconds | optional, try `2` for a fade |

For a light, blank override fields generate:

```json
"tap_action": {
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

Use overrides when the generated defaults are not what you want, or when using a
more generic `input_number` / `number` helper.

For light brightness, **Transition seconds** attempts to add Home Assistant
service data:

```json
"data": {
  "transition": 2
}
```

Many light integrations use that to fade to the selected brightness. However,
some GarminHomeAssistant versions do not pass extra action data from numeric
picker items, so this may be ignored even when the light supports transition.

## Add Submenu

Use **Add Submenu** to group related items.

Examples:

- Living Room
- Bedroom
- Security
- Media Controls

Items and submenus can be nested. Use the parent submenu field to choose where a
new item should appear.

## Menu Items

The Menu Items section shows the saved draft structure.

You can:

- move items up or down
- edit items
- remove items
- see which rows are submenus and which are normal items

After changing the structure, save the dashboard.

## JSON Editor

The JSON editor is an advanced escape hatch. Most users should use the form
controls.

Use JSON directly only when:

- copying a configuration for support
- inspecting generated GarminHomeAssistant output
- using a GarminHomeAssistant feature the builder does not yet expose

## Current Coverage

The builder currently supports:

- API URL and Configuration URL generation
- setup key rotation
- glance behavior
- info items
- toggle items
- run action items
- numeric picker items
- submenus and nested submenus
- secondary text templates
- emoji insertion
- entity/template suggestions
- item preview
- item edit/remove/reorder
- optional confirmation
- optional PIN requirement
- optional exit-after-action
- enabled/disabled items
- advanced JSON editing

The goal is to keep expanding form coverage so fewer users need the JSON editor.
