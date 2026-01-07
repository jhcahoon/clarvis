"""Clarvis conversation agent for Home Assistant."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import aiohttp

from homeassistant.components import conversation
from homeassistant.components.conversation import ConversationEntity, ConversationResult
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_API_HOST,
    CONF_API_PORT,
    DEFAULT_TIMEOUT,
    DOMAIN,
    EMAIL_KEYWORDS,
    GMAIL_QUERY_ENDPOINT,
)

if TYPE_CHECKING:
    from homeassistant.components.conversation import ConversationInput

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Clarvis conversation entity from a config entry."""
    async_add_entities([ClarvisConversationEntity(config_entry)])


class ClarvisConversationEntity(ConversationEntity):
    """Clarvis conversation agent entity."""

    _attr_has_entity_name = True
    _attr_name = "Clarvis"

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the entity."""
        self._config_entry = config_entry
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}"

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """Register the agent when added to hass."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self._config_entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister the agent when removed from hass."""
        conversation.async_unset_agent(self.hass, self._config_entry)
        await super().async_will_remove_from_hass()

    async def async_process(
        self, user_input: ConversationInput
    ) -> ConversationResult:
        """Process a sentence."""
        text = user_input.text.lower()

        # Check if this is an email-related query
        if self._is_email_query(text):
            return await self._handle_email_query(user_input)

        # Fall through to default agent for non-email queries
        return await self._fallback_to_default(user_input)

    def _is_email_query(self, text: str) -> bool:
        """Detect if the query is email-related."""
        return any(keyword in text for keyword in EMAIL_KEYWORDS)

    async def _handle_email_query(
        self, user_input: ConversationInput
    ) -> ConversationResult:
        """Handle email-related queries via Clarvis API."""
        host = self._config_entry.data.get(CONF_API_HOST)
        port = self._config_entry.data.get(CONF_API_PORT)
        url = f"http://{host}:{port}{GMAIL_QUERY_ENDPOINT}"

        session = async_get_clientsession(self.hass)

        try:
            async with session.post(
                url,
                json={"query": user_input.text},
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        response_text = data.get("response", "No response received")
                    else:
                        response_text = f"Error: {data.get('error', 'Unknown error')}"
                else:
                    response_text = f"API error: {resp.status}"
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Clarvis API: %s", err)
            response_text = "Sorry, I couldn't connect to the email service."
        except TimeoutError:
            _LOGGER.error("Timeout connecting to Clarvis API")
            response_text = "The email service took too long to respond."

        # Build the response
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response_text)

        return ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id,
        )

    async def _fallback_to_default(
        self, user_input: ConversationInput
    ) -> ConversationResult:
        """Fall back to default conversation agent."""
        # Get the default agent
        default_agent = conversation.async_get_agent(self.hass, None)

        if default_agent and default_agent != self:
            return await default_agent.async_process(user_input)

        # No default agent available
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(
            "I'm not sure how to help with that. Try asking about your emails."
        )

        return ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id,
        )
