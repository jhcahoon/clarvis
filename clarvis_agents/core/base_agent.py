"""Base agent abstractions for Clarvis multi-agent architecture."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

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
