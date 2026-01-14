"""Clarvis conversation agent for Home Assistant."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator, Literal, Optional

import aiohttp

from homeassistant.components import conversation
from homeassistant.components.conversation import ConversationEntity, ConversationResult
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Try to import ChatLog streaming support (HA 2025.7+)
try:
    from homeassistant.components.conversation import (
        ChatLog,
        async_get_result_from_chat_log,
    )
    from homeassistant.components.conversation.chat_log import (
        AssistantContentDeltaDict,
    )
    HAS_CHAT_LOG_STREAMING = True
except ImportError:
    HAS_CHAT_LOG_STREAMING = False
    ChatLog = None
    AssistantContentDeltaDict = dict  # type: ignore[misc]

    async def async_get_result_from_chat_log(
        user_input: Any, chat_log: Any
    ) -> ConversationResult:
        """Stub for older HA versions."""
        raise NotImplementedError

from .const import (
    CONF_API_HOST,
    CONF_API_PORT,
    DEFAULT_TIMEOUT,
    DOMAIN,
    HA_COMMAND_KEYWORDS,
    ORCHESTRATOR_QUERY_ENDPOINT,
    ORCHESTRATOR_STREAM_ENDPOINT,
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
    _attr_supports_streaming = True  # Enable HA streaming TTS support

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
        _LOGGER.info(
            "Clarvis registered (streaming TTS: %s, ChatLog API: %s)",
            self._attr_supports_streaming,
            HAS_CHAT_LOG_STREAMING,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister the agent when removed from hass."""
        conversation.async_unset_agent(self.hass, self._config_entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: ConversationInput,
        chat_log: ChatLog,
    ) -> ConversationResult:
        """Process with streaming to TTS via ChatLog.

        This method is called by the base class when ChatLog streaming is available.
        It streams response chunks directly to TTS for immediate playback.
        """
        if not HAS_CHAT_LOG_STREAMING:
            # Fall back to non-streaming if ChatLog API not available
            return await self._async_process_fallback(user_input)

        # Transform SSE stream to HA delta format
        async def _transform_stream() -> AsyncGenerator[
            AssistantContentDeltaDict, None
        ]:
            # Signal start of assistant message
            yield AssistantContentDeltaDict(role="assistant")

            # Stream chunks from API and yield as deltas
            async for chunk in self._stream_from_api(user_input):
                if chunk:
                    yield AssistantContentDeltaDict(content=chunk)

        try:
            # Feed deltas to ChatLog - this triggers streaming TTS!
            async for _ in chat_log.async_add_delta_content_stream(
                self.entity_id,
                _transform_stream(),
            ):
                pass  # ChatLog accumulates and streams to TTS

            # Return final result from accumulated chat_log
            return async_get_result_from_chat_log(user_input, chat_log)

        except Exception as err:
            _LOGGER.error("Streaming error: %s", err, exc_info=True)
            # Fall back to non-streaming on error
            return await self._async_process_fallback(user_input)

    async def _async_process_fallback(
        self, user_input: ConversationInput
    ) -> ConversationResult:
        """Fallback processing without ChatLog streaming."""
        # Try non-streaming orchestrator query
        result = await self._handle_orchestrator_query(user_input)
        if result is not None:
            return result

        # Orchestrator unavailable, fall back to default agent
        return await self._fallback_to_default(user_input)

    def _is_ha_command(self, text: str) -> bool:
        """Detect if query looks like a Home Assistant device command."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in HA_COMMAND_KEYWORDS)

    async def _stream_from_api(
        self, user_input: ConversationInput
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks from Clarvis API using SSE.

        Args:
            user_input: The user's conversation input.

        Yields:
            Text chunks as they arrive from the API.
        """
        host = self._config_entry.data.get(CONF_API_HOST)
        port = self._config_entry.data.get(CONF_API_PORT)
        url = f"http://{host}:{port}{ORCHESTRATOR_STREAM_ENDPOINT}"

        session = async_get_clientsession(self.hass)

        payload = {"query": user_input.text}
        if user_input.conversation_id:
            payload["session_id"] = user_input.conversation_id

        try:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning(
                        "Streaming API returned status %s", resp.status
                    )
                    return

                # Read SSE stream
                async for line in resp.content:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "text" in data:
                                yield data["text"]
                            elif "error" in data:
                                _LOGGER.error(
                                    "Streaming error: %s", data["error"]
                                )
                                yield f"Error: {data['error']}"
                        except json.JSONDecodeError:
                            _LOGGER.warning("Invalid JSON in SSE: %s", data_str)

        except aiohttp.ClientError as err:
            _LOGGER.error("Error streaming from Clarvis API: %s", err)
        except TimeoutError:
            _LOGGER.error("Timeout streaming from Clarvis API")

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
