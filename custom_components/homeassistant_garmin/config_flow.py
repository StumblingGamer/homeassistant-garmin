"""Config flow for Home Assistant for Garmin."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN, NAME


class HomeAssistantGarminConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Enable the Home Assistant for Garmin builder integration."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.FlowResult:
        """Create one integration entry that enables the sidebar builder."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title=NAME,
                data={
                    "mode": "builder",
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            errors={},
        )
