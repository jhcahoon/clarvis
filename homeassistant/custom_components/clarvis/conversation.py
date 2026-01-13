"""Clarvis conversation agent for Home Assistant."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, Optional

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
    HA_COMMAND_KEYWORDS,
    ORCHESTRATOR_QUERY_ENDPOINT,
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
        """Process a sentence through Clarvis orchestrator."""
        # Try orchestrator first
        result = await self._handle_orchestrator_query(user_input)

        if result is not None:
            return result

        # Orchestrator unavailable or can't handle, fall back to default agent
        return await self._fallback_to_default(user_input)

    def _is_ha_command(self, text: str) -> bool:
        """Detect if query looks like a Home Assistant device command."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in HA_COMMAND_KEYWORDS)

    async def _handle_orchestrator_query(
        self, user_input: ConversationInput
    ) -> Optional[ConversationResult]:
        """Handle query via Clarvis orchestrator API.

        Returns:
            ConversationResult if orchestrator handled the query,
            None if we should fall back to default agent.
        """
        host = self._config_entry.data.get(CONF_API_HOST)
        port = self._config_entry.data.get(CONF_API_PORT)
        url = f"http://{host}:{port}{ORCHESTRATOR_QUERY_ENDPOINT}"

        session = async_get_clientsession(self.hass)

        # Build request payload
        payload = {"query": user_input.text}

        # Use HA's conversation_id as session_id for continuity
        if user_input.conversation_id:
            payload["session_id"] = user_input.conversation_id

        try:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self._process_orchestrator_response(data, user_input)
                else:
                    _LOGGER.warning(
                        "Orchestrator API returned status %s", resp.status
                    )
                    return None  # Fall back to default agent

        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Clarvis API: %s", err)
            return None  # Fall back to default agent

        except TimeoutError:
            _LOGGER.error("Timeout connecting to Clarvis API")
            return None  # Fall back to default agent

    def _process_orchestrator_response(
        self, data: dict, user_input: ConversationInput
    ) -> Optional[ConversationResult]:
        """Process the orchestrator response and determine next action.

        Args:
            data: Response JSON from orchestrator API
            user_input: Original user input

        Returns:
            ConversationResult if we should return this response,
            None if we should fall back to default agent.
        """
        success = data.get("success", False)
        response_text = data.get("response", "")
        agent_name = data.get("agent_name", "")
        session_id = data.get("session_id", user_input.conversation_id)
        error = data.get("error")
        metadata = data.get("metadata", {})

        # Case 1: Error occurred
        if not success and error:
            _LOGGER.warning("Orchestrator error: %s", error)
            response_text = f"Sorry, there was an error: {error}"
            return self._build_response(response_text, user_input, session_id)

        # Case 2: Successful response from specialized agent
        if success and agent_name not in ("orchestrator",):
            return self._build_response(response_text, user_input, session_id)

        # Case 3: Orchestrator handled directly (greetings, thanks, or fallback)
        if success and agent_name == "orchestrator":
            # Check if this was a fallback (no agent matched)
            is_fallback = metadata.get("fallback", False)

            if is_fallback and self._is_ha_command(user_input.text):
                # Query looks like HA command, let default agent handle it
                _LOGGER.debug(
                    "Orchestrator fallback for HA command, delegating to default"
                )
                return None

            # Orchestrator handled it (greeting, thanks, or genuine fallback)
            return self._build_response(response_text, user_input, session_id)

        # Case 4: Empty or unexpected response
        if not response_text:
            _LOGGER.warning("Empty response from orchestrator")
            return None

        return self._build_response(response_text, user_input, session_id)

    def _build_response(
        self,
        response_text: str,
        user_input: ConversationInput,
        session_id: Optional[str] = None,
    ) -> ConversationResult:
        """Build a ConversationResult with the given response text."""
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response_text)

        return ConversationResult(
            response=intent_response,
            conversation_id=session_id or user_input.conversation_id,
        )

    async def _fallback_to_default(
        self, user_input: ConversationInput
    ) -> ConversationResult:
        """Fall back to default conversation agent."""
        default_agent = conversation.async_get_agent(self.hass, None)

        if default_agent and default_agent != self:
            return await default_agent.async_process(user_input)

        # No default agent available
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(
            "I'm sorry, I couldn't connect to Clarvis and no other assistant is available."
        )

        return ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id,
        )
