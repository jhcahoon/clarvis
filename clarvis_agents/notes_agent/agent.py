"""Notes Agent implementation for managing notes, lists, and reminders."""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from anthropic import Anthropic

from ..core import AgentCapability, AgentResponse, BaseAgent
from ..core.context import ConversationContext
from .config import NotesAgentConfig, RateLimiter
from .prompts import SYSTEM_PROMPT
from .storage import NotesStorage
from .tools import (
    add_to_list_impl,
    clear_list_impl,
    create_note_impl,
    delete_note_impl,
    get_note_impl,
    list_notes_impl,
    remove_from_list_impl,
    set_storage,
    update_note_impl,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotesAgent(BaseAgent):
    """Notes and lists management agent."""

    def __init__(self, config: Optional[NotesAgentConfig] = None, client: Optional[Anthropic] = None):
        """Initialize Notes Agent.

        Args:
            config: Configuration for the agent. If None, uses default config.
            client: Optional Anthropic client. If None, creates one.
        """
        self.config = config or NotesAgentConfig()
        self._setup_logging()
        self.rate_limiter = RateLimiter(
            max_calls=self.config.max_requests_per_minute,
            time_window=timedelta(minutes=1),
        )
        # Initialize storage and set it for the tools module
        self._storage = NotesStorage(notes_dir=self.config.notes_dir)
        set_storage(self._storage)
        self._client = client or Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self._tools = self._build_tools()

    # BaseAgent interface implementation

    @property
    def name(self) -> str:
        """Unique identifier for this agent."""
        return "notes"

    @property
    def description(self) -> str:
        """Human-readable description of what this agent does."""
        return "Manage notes, lists, reminders, and quick information"

    @property
    def capabilities(self) -> list[AgentCapability]:
        """List of capabilities this agent provides."""
        return [
            AgentCapability(
                name="manage_lists",
                description="Create and manage lists like grocery, shopping, or to-do",
                keywords=["list", "grocery", "shopping", "todo", "add", "remove"],
                examples=["Add milk to my grocery list", "What's on my shopping list?"],
            ),
            AgentCapability(
                name="reminders",
                description="Store and retrieve reminders",
                keywords=["remind", "reminder", "remember", "don't forget"],
                examples=["Remind me to call the dentist", "What are my reminders?"],
            ),
            AgentCapability(
                name="notes",
                description="Save and retrieve general notes and information",
                keywords=["note", "save", "remember", "code", "information"],
                examples=["Take a note: the garage code is 1234", "What's the garage code?"],
            ),
            AgentCapability(
                name="list_management",
                description="View, clear, and delete notes and lists",
                keywords=["show", "clear", "delete", "what notes"],
                examples=["What notes do I have?", "Clear my grocery list"],
            ),
        ]

    async def process(
        self, query_text: str, context: Optional[ConversationContext] = None
    ) -> AgentResponse:
        """Process a query and return a response."""
        try:
            response_text = await self._handle_query(query_text)
            return AgentResponse(
                content=response_text,
                success=True,
                agent_name=self.name,
            )
        except Exception as e:
            logger.error(f"Error in process: {e}", exc_info=True)
            return AgentResponse(
                content=f"Error handling notes request: {str(e)}",
                success=False,
                agent_name=self.name,
                error=str(e),
            )

    def health_check(self) -> bool:
        """Check if the agent is operational."""
        # Check if storage directory is accessible
        try:
            self.config.notes_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    async def stream(
        self, query_text: str, context: Optional[ConversationContext] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks for a query.

        Uses Anthropic SDK with tool calling for notes operations.

        Args:
            query_text: Natural language query about notes.
            context: Optional conversation context (not currently used).

        Yields:
            String chunks of the response as they become available.
        """
        # Check rate limit
        if not self.rate_limiter.check_rate_limit():
            yield "Rate limit exceeded. Please wait before making another request."
            return

        logger.info(f"Streaming notes query: {query_text[:100]}...")

        try:
            messages = [{"role": "user", "content": query_text}]

            # Agentic loop with tool calling
            for _ in range(self.config.max_turns):
                response = self._client.messages.create(
                    model=self.config.model,
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    tools=self._tools,
                    messages=messages,
                )

                # Check if we need to handle tool calls
                if response.stop_reason == "tool_use":
                    # Process tool calls
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            result = await self._execute_tool(block.name, block.input)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            })

                    # Add assistant message and tool results to conversation
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})
                else:
                    # Final response - stream it
                    # Since we already have the response, just yield the text
                    for block in response.content:
                        if hasattr(block, "text"):
                            yield block.text
                    break

            logger.info("Notes query streaming completed")

        except Exception as e:
            logger.error(f"Error streaming notes query: {e}", exc_info=True)
            yield f"Sorry, I encountered an error: {str(e)}"

    # Private methods

    def _setup_logging(self) -> None:
        """Configure logging for notes access."""
        self.config.log_dir.mkdir(parents=True, exist_ok=True)

        log_file = self.config.log_dir / f"access_{datetime.now():%Y%m%d}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
        logger.info("Notes Agent logging initialized")

    def _build_tools(self) -> list[dict]:
        """Build Anthropic-format tool definitions."""
        return [
            {
                "name": "create_note",
                "description": "Create a new note or list. Use note_type='list' for grocery lists, shopping lists, todos. Use note_type='general' for codes, information, free-form notes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Title for the note"},
                        "note_type": {"type": "string", "enum": ["list", "reminder", "general"], "description": "Type of note"},
                        "content": {"type": "string", "description": "Content for general notes", "default": ""},
                        "items": {"type": "array", "items": {"type": "string"}, "description": "Initial items for lists", "default": []},
                    },
                    "required": ["title", "note_type"],
                },
            },
            {
                "name": "add_to_list",
                "description": "Add items to a list (grocery, shopping, reminders, etc.). Creates the list if it doesn't exist.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "list_name": {"type": "string", "description": "Name of the list"},
                        "items": {"type": "array", "items": {"type": "string"}, "description": "Items to add"},
                    },
                    "required": ["list_name", "items"],
                },
            },
            {
                "name": "remove_from_list",
                "description": "Remove items from a list.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "list_name": {"type": "string", "description": "Name of the list"},
                        "items": {"type": "array", "items": {"type": "string"}, "description": "Items to remove"},
                    },
                    "required": ["list_name", "items"],
                },
            },
            {
                "name": "get_note",
                "description": "Get a note or list by name. Returns the content or items.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "note_name": {"type": "string", "description": "Name of the note or list"},
                    },
                    "required": ["note_name"],
                },
            },
            {
                "name": "list_notes",
                "description": "List all notes, optionally filtered by type.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "note_type": {"type": "string", "enum": ["list", "reminder", "general"], "description": "Filter by note type (optional)"},
                    },
                    "required": [],
                },
            },
            {
                "name": "update_note",
                "description": "Update the content of an existing note.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "note_name": {"type": "string", "description": "Name of the note"},
                        "content": {"type": "string", "description": "New content"},
                    },
                    "required": ["note_name", "content"],
                },
            },
            {
                "name": "delete_note",
                "description": "Delete a note or list.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "note_name": {"type": "string", "description": "Name of the note to delete"},
                    },
                    "required": ["note_name"],
                },
            },
            {
                "name": "clear_list",
                "description": "Clear all items from a list (keeps the list but removes all items).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "list_name": {"type": "string", "description": "Name of the list to clear"},
                    },
                    "required": ["list_name"],
                },
            },
        ]

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool and return the result."""
        logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

        if tool_name == "create_note":
            return await create_note_impl(
                title=tool_input["title"],
                note_type=tool_input["note_type"],
                content=tool_input.get("content", ""),
                items=tool_input.get("items"),
            )
        elif tool_name == "add_to_list":
            return await add_to_list_impl(
                list_name=tool_input["list_name"],
                items=tool_input["items"],
            )
        elif tool_name == "remove_from_list":
            return await remove_from_list_impl(
                list_name=tool_input["list_name"],
                items=tool_input["items"],
            )
        elif tool_name == "get_note":
            return await get_note_impl(note_name=tool_input["note_name"])
        elif tool_name == "list_notes":
            return await list_notes_impl(note_type=tool_input.get("note_type"))
        elif tool_name == "update_note":
            return await update_note_impl(
                note_name=tool_input["note_name"],
                content=tool_input["content"],
            )
        elif tool_name == "delete_note":
            return await delete_note_impl(note_name=tool_input["note_name"])
        elif tool_name == "clear_list":
            return await clear_list_impl(list_name=tool_input["list_name"])
        else:
            return f"Unknown tool: {tool_name}"

    async def _handle_query(self, query_text: str) -> str:
        """Handle a notes query.

        Args:
            query_text: Natural language query about notes

        Returns:
            Agent's response as string
        """
        # Check rate limit
        if not self.rate_limiter.check_rate_limit():
            return "Rate limit exceeded. Please wait before making another request."

        logger.info(f"Processing notes query: {query_text[:100]}...")

        try:
            messages = [{"role": "user", "content": query_text}]

            # Agentic loop with tool calling
            for _ in range(self.config.max_turns):
                response = self._client.messages.create(
                    model=self.config.model,
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    tools=self._tools,
                    messages=messages,
                )

                # Check if we need to handle tool calls
                if response.stop_reason == "tool_use":
                    # Process tool calls
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            result = await self._execute_tool(block.name, block.input)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            })

                    # Add assistant message and tool results to conversation
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})
                else:
                    # Final response
                    response_text = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            response_text += block.text

                    if not response_text:
                        response_text = "I processed your request but couldn't generate a response."

                    logger.info("Notes query processed successfully")
                    return response_text

            return "I wasn't able to complete your request within the allowed turns."

        except Exception as e:
            logger.error(f"Error handling notes query: {e}", exc_info=True)
            return f"Sorry, I encountered an error: {str(e)}"

    def handle_query(self, query_text: str) -> str:
        """Main entry point for handling notes queries (synchronous wrapper).

        Args:
            query_text: Natural language query about notes

        Returns:
            Agent's response as string
        """
        return asyncio.run(self._handle_query(query_text))


def create_notes_agent(config: Optional[NotesAgentConfig] = None) -> NotesAgent:
    """Factory function to create Notes agent.

    Args:
        config: Optional custom configuration

    Returns:
        Configured NotesAgent instance
    """
    return NotesAgent(config=config)


if __name__ == "__main__":
    agent = create_notes_agent()
    print(agent.handle_query("Add milk to my grocery list"))
