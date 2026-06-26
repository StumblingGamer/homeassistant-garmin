# Changelog

## [0.1.0] - 2026-06-25

Initial release.

### Added

- **Garmin sidebar panel** — adds a dedicated Garmin page to the Home Assistant sidebar
- **Dashboard builder UI** — visual menu builder; no hand-writing JSON required
- **Entity picker** — browse and select Home Assistant entities by domain
- **Menu item types** — support for info rows, toggles, action rows, number pickers, and submenus
- **Watch row content templates** — write Home Assistant templates for watch display text, with live preview
- **Emoji picker** — insert emoji into watch labels directly from the builder
- **Automatic behavior detection** — sensible default behavior per entity type (toggle for switches, info for sensors, etc.)
- **Nested submenus** — build multi-level watch menus
- **Reorder, edit, and remove items** — full menu management from the builder
- **View Garmin JSON** — inspect the generated GarminHomeAssistant config before saving
- **Watch App Settings page** — displays the API URL and Configuration URL to paste into GarminHomeAssistant
- **Nabu Casa / base URL detection** — automatically detects your Home Assistant external URL
- **Unsaved change detection** — warns before leaving the builder with unsaved changes
- **HACS support** — installable as a custom HACS repository
