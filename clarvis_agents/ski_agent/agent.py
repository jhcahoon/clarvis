"""Ski Agent implementation for Mt Hood Meadows conditions."""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from anthropic import Anthropic

from ..core import AgentCapability, AgentResponse, BaseAgent
from ..core.context import ConversationContext
from .config import CachedConditions, RateLimiter, SkiAgentConfig
from .prompts import SYSTEM_PROMPT
from .tools import fetch_ski_conditions_impl

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SkiAgent(BaseAgent):
    """Ski conditions reporter agent for Mt Hood Meadows."""

    def __init__(self, config: Optional[SkiAgentConfig] = None, client: Optional[Anthropic] = None):
        """Initialize Ski Agent.

        Args:
            config: Configuration for the agent. If None, uses default config.
            client: Optional Anthropic client. If None, creates one.
        """
        self.config = config or SkiAgentConfig()
        self._setup_logging()
        self.rate_limiter = RateLimiter(
            max_calls=self.config.max_requests_per_minute,
            time_window=timedelta(minutes=1),
        )
        self._cache: Optional[CachedConditions] = None
        self._client = client or Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

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

        Pre-fetches ski conditions, then streams Claude's response.

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
            # Pre-fetch ski conditions
            conditions_data = await fetch_ski_conditions_impl()

            # Build prompt with conditions data
            prompt = self._build_prompt_with_data(query_text, conditions_data)

            # Stream response from Anthropic
            with self._client.messages.stream(
                model=self.config.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
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

    def _build_prompt_with_data(self, user_query: str, conditions_data: str) -> str:
        """Build prompt with pre-fetched conditions data.

        Args:
            user_query: The user's original query
            conditions_data: Raw conditions data from the ski conditions page

        Returns:
            Prompt string with conditions data included
        """
        return f"""Here are the current ski conditions from Mt Hood Meadows:

<conditions>
{conditions_data}
</conditions>

Based on this data, please answer the following question:
{user_query}"""

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
            # Pre-fetch ski conditions
            conditions_data = await fetch_ski_conditions_impl()

            # Build prompt with conditions data
            prompt = self._build_prompt_with_data(query_text, conditions_data)

            # Get response from Anthropic
            response = self._client.messages.create(
                model=self.config.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

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
