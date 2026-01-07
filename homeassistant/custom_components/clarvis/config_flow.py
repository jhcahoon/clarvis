"""Config flow for Clarvis AI Assistant integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_HOST,
    CONF_API_PORT,
    DEFAULT_API_HOST,
    DEFAULT_API_PORT,
    DOMAIN,
    HEALTH_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


class ClarvisConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Clarvis AI Assistant."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Test connection to the API
            if await self._test_connection(
                user_input[CONF_API_HOST], user_input[CONF_API_PORT]
            ):
                # Prevent duplicate entries
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="Clarvis AI Assistant",
                    data=user_input,
                )
            errors["base"] = "cannot_connect"

        # Show configuration form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_HOST, default=DEFAULT_API_HOST): str,
                    vol.Required(CONF_API_PORT, default=DEFAULT_API_PORT): int,
                }
            ),
            errors=errors,
        )

    async def _test_connection(self, host: str, port: int) -> bool:
        """Test connection to the Clarvis API."""
        url = f"http://{host}:{port}{HEALTH_ENDPOINT}"

        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("status") == "healthy"
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("Connection test failed: %s", err)
        except Exception as err:
            _LOGGER.error("Unexpected error during connection test: %s", err)

        return False

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry,
    ) -> ClarvisOptionsFlow:
        """Get the options flow for this handler."""
        return ClarvisOptionsFlow()


class ClarvisOptionsFlow(OptionsFlow):
    """Handle Clarvis options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_HOST,
                        default=self.config_entry.data.get(
                            CONF_API_HOST, DEFAULT_API_HOST
                        ),
                    ): str,
                    vol.Required(
                        CONF_API_PORT,
                        default=self.config_entry.data.get(
                            CONF_API_PORT, DEFAULT_API_PORT
                        ),
                    ): int,
                }
            ),
        )
