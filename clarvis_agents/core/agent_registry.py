"""Agent registry for Clarvis multi-agent architecture."""

from typing import Optional

from .base_agent import AgentCapability, BaseAgent


class AgentRegistry:
    """Central registry for all available agents (singleton)."""

    _instance: Optional["AgentRegistry"] = None
    _agents: dict[str, BaseAgent]

    def __new__(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
        return cls._instance

    def register(self, agent: BaseAgent) -> None:
        """Register an agent by its name.

        Args:
            agent: The agent to register.
        """
        self._agents[agent.name] = agent

    def unregister(self, name: str) -> None:
        """Remove an agent from the registry.

        Args:
            name: The name of the agent to remove.
        """
        if name in self._agents:
            del self._agents[name]

    def get(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name.

        Args:
            name: The name of the agent to retrieve.

        Returns:
            The agent if found, None otherwise.
        """
        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        """List all registered agent names.

        Returns:
            List of registered agent names.
        """
        return list(self._agents.keys())

    def get_all_capabilities(self) -> dict[str, list[AgentCapability]]:
        """Get capabilities for all registered agents.

        Returns:
            Dictionary mapping agent names to their capabilities.
        """
        return {name: agent.capabilities for name, agent in self._agents.items()}

    def health_check_all(self) -> dict[str, bool]:
        """Run health checks on all registered agents.

        Returns:
            Dictionary mapping agent names to their health status.
        """
        return {name: agent.health_check() for name, agent in self._agents.items()}

    def clear(self) -> None:
        """Clear all registered agents (useful for testing)."""
        self._agents.clear()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None
