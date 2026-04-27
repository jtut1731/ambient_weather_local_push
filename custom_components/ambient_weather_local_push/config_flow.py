"""Config flow for Ambient Weather Local Push."""

from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol
from yarl import URL

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.helpers.network import get_url

from .const import CONF_NAME, DOMAIN


class AmbientWeatherLocalPushConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle an Ambient Weather Local Push config flow."""

    VERSION = 1
    _webhook_id: str

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is None:
            self._webhook_id = secrets.token_hex(16)
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {vol.Required(CONF_NAME, default="Ambient Weather Station"): str}
                ),
                errors=errors,
            )

        base_url = URL(get_url(self.hass))
        assert base_url.host

        await self.async_set_unique_id(self._webhook_id)
        self._abort_if_unique_id_configured()

        path = f"{webhook.async_generate_path(self._webhook_id)}?q=1"

        return self.async_create_entry(
            title=user_input[CONF_NAME],
            data={
                CONF_NAME: user_input[CONF_NAME],
                CONF_WEBHOOK_ID: self._webhook_id,
            },
            description_placeholders={
                "host": base_url.host,
                "path": path,
                "port": str(
                    base_url.port or (443 if base_url.scheme == "https" else 80)
                ),
            },
        )
