"""Config flow for Companion Bluetooth Proxy integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import webhook
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .constants import CONF_WEBHOOK, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _create_webhook(hass: HomeAssistant) -> tuple[str, str]:
    """Generate a new webhook ID and URL."""
    webhook_id = webhook.async_generate_id()
    webhook_url = webhook.async_generate_url(hass, webhook_id)
    return webhook_id, webhook_url


def _create_schema(hass: HomeAssistant) -> vol.Schema:
    """Create the configuration schema with webhook defaults."""
    hook_id, hook_url = _create_webhook(hass)
    schema = vol.Schema(
        {
            vol.Required("name"): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(CONF_WEBHOOK, default=hook_id): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional("webhook_url", default=hook_url): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.URL,
                    multiline=False,
                )
            ),
        }
    )
    return schema


class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Companion Bluetooth Proxy."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug("Processing config flow input: %s", user_input)

            # Set unique ID based on the proxy name to prevent duplicates
            await self.async_set_unique_id(user_input["name"])
            self._abort_if_unique_id_configured()

            # Create the config entry
            return self.async_create_entry(
                title=user_input["name"],
                data={
                    CONF_WEBHOOK: user_input[CONF_WEBHOOK],
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_create_schema(self.hass),
            errors=errors,
        )