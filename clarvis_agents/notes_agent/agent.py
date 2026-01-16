"""Notes Agent implementation for managing notes, lists, and reminders."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from claude_agent_sdk import ClaudeAgentOptions, query

from ..core import AgentCapability, AgentResponse, BaseAgent
from ..core.context import ConversationContext
from .config import NotesAgentConfig, RateLimiter
from .prompts import SYSTEM_PROMPT
from .storage import NotesStorage
from .tools import notes_tools_server, set_storage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotesAgent(BaseAgent):
    """Notes and lists management agent."""

    def __init__(self, config: Optional[NotesAgentConfig] = None):
        """Initialize Notes Agent.

        Args:
            config: Configuration for the agent. If None, uses default config.
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

        Yields text chunks as they arrive from the Claude SDK.

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
            options = self._build_agent_options()

            async for message in query(prompt=query_text, options=options):
                # Extract text from different message types and yield immediately
                if hasattr(message, "result"):
                    text = str(message.result)
                    if text:
                        yield text
                elif hasattr(message, "text"):
                    text = str(message.text)
                    if text:
                        yield text
                elif hasattr(message, "content"):
                    if isinstance(message.content, str):
                        if message.content:
                            yield message.content
                    elif isinstance(message.content, list):
                        for block in message.content:
                            if hasattr(block, "text") and block.text:
                                yield block.text

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

    def _build_agent_options(self) -> ClaudeAgentOptions:
        """Build ClaudeAgentOptions with native tools.

        Returns:
            Configured ClaudeAgentOptions for the query
        """
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"notes_tools": notes_tools_server},
            model=self.config.model,
            max_turns=self.config.max_turns,
            # Skip permission checks for native tools
            extra_args={"dangerously-skip-permissions": None},
        )

        return options

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
            options = self._build_agent_options()

            # Stream response from Claude Agent SDK
            response_text = ""
            async for message in query(prompt=query_text, options=options):
                if hasattr(message, "result"):
                    response_text += str(message.result)
                elif hasattr(message, "text"):
                    response_text += str(message.text)
                elif hasattr(message, "content"):
                    if isinstance(message.content, str):
                        response_text += message.content
                    elif isinstance(message.content, list):
                        for block in message.content:
                            if hasattr(block, "text"):
                                response_text += block.text

            if not response_text:
                response_text = "I processed your request but couldn't generate a response."

            logger.info("Notes query processed successfully")
            return response_text

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
