"""Ski Agent implementation for Mt Hood Meadows conditions."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from claude_agent_sdk import ClaudeAgentOptions, query

from ..core import AgentCapability, AgentResponse, BaseAgent
from ..core.context import ConversationContext
from .config import CachedConditions, RateLimiter, SkiAgentConfig
from .prompts import SYSTEM_PROMPT
from .tools import ski_tools_server

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SkiAgent(BaseAgent):
    """Ski conditions reporter agent for Mt Hood Meadows."""

    def __init__(self, config: Optional[SkiAgentConfig] = None):
        """Initialize Ski Agent.

        Args:
            config: Configuration for the agent. If None, uses default config.
        """
        self.config = config or SkiAgentConfig()
        self._setup_logging()
        self.rate_limiter = RateLimiter(
            max_calls=self.config.max_requests_per_minute,
            time_window=timedelta(minutes=1),
        )
        self._cache: Optional[CachedConditions] = None

    # BaseAgent interface implementation

    @property
    def name(self) -> str:
        """Unique identifier for this agent."""
        return "ski"

    @property
    def description(self) -> str:
        """Human-readable description of what this agent does."""
        return "Report ski conditions for Mt Hood Meadows"

    @property
    def capabilities(self) -> list[AgentCapability]:
        """List of capabilities this agent provides."""
        return [
            AgentCapability(
                name="snow_conditions",
                description="Report snow depths and recent snowfall",
                keywords=["snow", "powder", "depth", "base", "inches"],
                examples=["How much snow at Meadows?", "What's the base depth?"],
            ),
            AgentCapability(
                name="lift_status",
                description="Report which lifts are open or on hold",
                keywords=["lift", "lifts", "open", "running", "closed"],
                examples=["Are the lifts running?", "Which lifts are open?"],
            ),
            AgentCapability(
                name="weather",
                description="Report mountain weather conditions",
                keywords=["weather", "temperature", "wind", "visibility"],
                examples=["What's the weather at Meadows?", "How cold is it?"],
            ),
            AgentCapability(
                name="full_report",
                description="Comprehensive ski conditions report",
                keywords=["report", "conditions", "ski report"],
                examples=["What's the ski report?", "Give me the full conditions"],
            ),
        ]

    async def process(
        self, query_text: str, context: Optional[ConversationContext] = None
    ) -> AgentResponse:
        """Process a query and return a response."""
        try:
            response_text = await self._get_conditions(query_text)
            return AgentResponse(
                content=response_text,
                success=True,
                agent_name=self.name,
            )
        except Exception as e:
            logger.error(f"Error in process: {e}", exc_info=True)
            return AgentResponse(
                content=f"Error getting ski conditions: {str(e)}",
                success=False,
                agent_name=self.name,
                error=str(e),
            )

    def health_check(self) -> bool:
        """Check if the agent is operational."""
        return True

    async def stream(
        self, query_text: str, context: Optional[ConversationContext] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks for a query.

        Yields text chunks as they arrive from the Claude SDK.

        Args:
            query_text: Natural language query about ski conditions.
            context: Optional conversation context (not currently used).

        Yields:
            String chunks of the response as they become available.
        """
        # Check rate limit
        if not self.rate_limiter.check_rate_limit():
            yield "Rate limit exceeded. Please wait before making another request."
            return

        logger.info(f"Streaming ski conditions query: {query_text[:100]}...")

        try:
            options = self._build_agent_options()

            # Build prompt that instructs agent to fetch conditions
            prompt = self._build_conditions_prompt(query_text)

            async for message in query(prompt=prompt, options=options):
                text = self._extract_text_from_message(message)
                if text:
                    yield text

            logger.info("Ski conditions query streaming completed")

        except Exception as e:
            logger.error(f"Error streaming ski conditions: {e}", exc_info=True)
            yield f"Sorry, I couldn't get the ski conditions: {str(e)}"

    # Private methods

    def _setup_logging(self) -> None:
        """Configure logging for ski conditions access."""
        self.config.log_dir.mkdir(parents=True, exist_ok=True)

        log_file = self.config.log_dir / f"access_{datetime.now():%Y%m%d}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
        logger.info("Ski Agent logging initialized")

    def _build_agent_options(self) -> ClaudeAgentOptions:
        """Build ClaudeAgentOptions with native tools.

        Returns:
            Configured ClaudeAgentOptions for the query
        """
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"ski_tools": ski_tools_server},
            model=self.config.model,
            max_turns=self.config.max_turns,
            # Skip permission checks for native tools
            extra_args={"dangerously-skip-permissions": None},
        )

        return options

    def _build_conditions_prompt(self, user_query: str) -> str:
        """Build prompt that instructs agent to fetch and report conditions.

        Args:
            user_query: The user's original query

        Returns:
            Prompt string for the agent
        """
        return f"""Use the fetch_ski_conditions tool to get the current conditions, then answer:

{user_query}"""

    def _extract_text_from_message(self, message: object) -> str:
        """Extract text content from a Claude SDK message.

        Handles various message types returned by the SDK including
        result objects, text objects, and content blocks.

        Args:
            message: A message object from the Claude SDK query stream.

        Returns:
            Extracted text content, or empty string if no text found.
        """
        if hasattr(message, "result"):
            return str(message.result)
        elif hasattr(message, "text"):
            return str(message.text)
        elif hasattr(message, "content"):
            if isinstance(message.content, str):
                return message.content
            elif isinstance(message.content, list):
                parts = []
                for block in message.content:
                    if hasattr(block, "text") and block.text:
                        parts.append(block.text)
                return "".join(parts)
        return ""

    async def _get_conditions(self, query_text: str) -> str:
        """Get ski conditions for a query.

        Args:
            query_text: Natural language query about ski conditions

        Returns:
            Agent's response as string
        """
        # Check rate limit
        if not self.rate_limiter.check_rate_limit():
            return "Rate limit exceeded. Please wait before making another request."

        logger.info(f"Processing ski conditions query: {query_text[:100]}...")

        try:
            options = self._build_agent_options()
            prompt = self._build_conditions_prompt(query_text)

            # Stream response from Claude Agent SDK
            response_text = ""
            async for message in query(prompt=prompt, options=options):
                response_text += self._extract_text_from_message(message)

            if not response_text:
                response_text = (
                    "I couldn't retrieve the ski conditions. Please try again."
                )

            logger.info("Ski conditions query processed successfully")
            return response_text

        except Exception as e:
            logger.error(f"Error getting ski conditions: {e}", exc_info=True)
            return f"Sorry, I couldn't get the ski conditions: {str(e)}"

    def get_conditions(self, query_text: str) -> str:
        """Main entry point for getting ski conditions (synchronous wrapper).

        Args:
            query_text: Natural language query about ski conditions

        Returns:
            Agent's response as string
        """
        return asyncio.run(self._get_conditions(query_text))


def create_ski_agent() -> SkiAgent:
    """Factory function to create Ski agent.

    Returns:
        Configured SkiAgent instance
    """
    config = SkiAgentConfig()
    return SkiAgent(config)


if __name__ == "__main__":
    agent = create_ski_agent()
    print(agent.get_conditions("What's the ski report at Meadows?"))
