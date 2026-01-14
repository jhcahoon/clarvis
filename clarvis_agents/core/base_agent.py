"""Base agent abstractions for Clarvis multi-agent architecture."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, AsyncGenerator, Optional

if TYPE_CHECKING:
    from .context import ConversationContext


@dataclass
class AgentResponse:
    """Standardized response from any agent."""

    content: str
    success: bool
    agent_name: str
    metadata: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class AgentCapability:
    """Describes what an agent can do."""

    name: str
    description: str
    keywords: list[str]  # For fast-path routing
    examples: list[str]  # For LLM routing context


class BaseAgent(ABC):
    """Abstract base class for all Clarvis agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this agent does."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> list[AgentCapability]:
        """List of capabilities this agent provides."""
        ...

    @abstractmethod
    async def process(
        self, query: str, context: Optional["ConversationContext"] = None
    ) -> AgentResponse:
        """Process a query and return a response.

        Args:
            query: The user's query to process.
            context: Optional conversation context for multi-turn conversations.

        Returns:
            AgentResponse with the result of processing the query.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the agent is operational.

        Returns:
            True if the agent is healthy and ready to process queries.
        """
        ...

    async def stream(
        self, query: str, context: Optional["ConversationContext"] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks for a query.

        This is an optional method for agents that support streaming.
        Default implementation falls back to process() and yields the
        complete response as a single chunk.

        Args:
            query: The user's query to process.
            context: Optional conversation context for multi-turn conversations.

        Yields:
            String chunks of the response as they become available.
        """
        # Default implementation: fall back to process() and yield complete response
        response = await self.process(query, context)
        yield response.content
