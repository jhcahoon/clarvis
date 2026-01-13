"""Tests for AgentRegistry singleton (Issue #18)."""

import pytest
from typing import Optional

from clarvis_agents.core import (
    AgentCapability,
    AgentRegistry,
    AgentResponse,
    BaseAgent,
    ConversationContext,
)


class MockAgent(BaseAgent):
    """Mock agent for testing registry functionality."""

    def __init__(self, agent_name: str, healthy: bool = True):
        self._name = agent_name
        self._healthy = healthy

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Mock agent: {self._name}"

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name=f"{self._name}_cap",
                description=f"Capability for {self._name}",
                keywords=[self._name],
                examples=[f"use {self._name}"],
            )
        ]

    async def process(
        self, query: str, context: Optional[ConversationContext] = None
    ) -> AgentResponse:
        return AgentResponse(
            content=f"Response from {self._name}",
            success=True,
            agent_name=self._name,
        )

    def health_check(self) -> bool:
        return self._healthy


class MockAgentNoCapabilities(BaseAgent):
    """Mock agent with empty capabilities list."""

    def __init__(self, agent_name: str):
        self._name = agent_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Mock agent with no capabilities: {self._name}"

    @property
    def capabilities(self) -> list[AgentCapability]:
        return []

    async def process(
        self, query: str, context: Optional[ConversationContext] = None
    ) -> AgentResponse:
        return AgentResponse(
            content=f"Response from {self._name}",
            success=True,
            agent_name=self._name,
        )

    def health_check(self) -> bool:
        return True


class TestAgentRegistry:
    """Test suite for AgentRegistry singleton."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the registry before and after each test."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    def test_registry_is_singleton(self):
        """Test that AgentRegistry returns the same instance."""
        registry1 = AgentRegistry()
        registry2 = AgentRegistry()
        assert registry1 is registry2

    def test_register_adds_agent(self):
        """Test that register adds an agent to the registry."""
        registry = AgentRegistry()
        agent = MockAgent("test")

        registry.register(agent)

        assert registry.get("test") is agent

    def test_get_returns_registered_agent(self):
        """Test that get returns a registered agent."""
        registry = AgentRegistry()
        agent = MockAgent("test")
        registry.register(agent)

        result = registry.get("test")

        assert result is agent

    def test_get_returns_none_for_unregistered_agent(self):
        """Test that get returns None for unregistered agent."""
        registry = AgentRegistry()
        result = registry.get("nonexistent")
        assert result is None

    def test_list_agents_returns_registered_names(self):
        """Test that list_agents returns all registered agent names."""
        registry = AgentRegistry()
        registry.register(MockAgent("agent1"))
        registry.register(MockAgent("agent2"))
        registry.register(MockAgent("agent3"))

        names = registry.list_agents()

        assert set(names) == {"agent1", "agent2", "agent3"}

    def test_list_agents_empty_registry(self):
        """Test list_agents with empty registry."""
        registry = AgentRegistry()
        assert registry.list_agents() == []

    def test_unregister_removes_agent(self):
        """Test that unregister removes an agent."""
        registry = AgentRegistry()
        agent = MockAgent("test")
        registry.register(agent)

        registry.unregister("test")

        assert registry.get("test") is None
        assert "test" not in registry.list_agents()

    def test_unregister_nonexistent_agent_does_nothing(self):
        """Test that unregister for nonexistent agent doesn't raise."""
        registry = AgentRegistry()
        # Should not raise
        registry.unregister("nonexistent")

    def test_get_all_capabilities_returns_dict(self):
        """Test that get_all_capabilities returns capabilities dict."""
        registry = AgentRegistry()
        registry.register(MockAgent("agent1"))
        registry.register(MockAgent("agent2"))

        capabilities = registry.get_all_capabilities()

        assert "agent1" in capabilities
        assert "agent2" in capabilities
        assert len(capabilities["agent1"]) == 1
        assert capabilities["agent1"][0].name == "agent1_cap"

    def test_health_check_all_returns_dict(self):
        """Test that health_check_all returns health status dict."""
        registry = AgentRegistry()
        registry.register(MockAgent("agent1"))
        registry.register(MockAgent("agent2"))

        health = registry.health_check_all()

        assert health == {"agent1": True, "agent2": True}

    def test_clear_removes_all_agents(self):
        """Test that clear removes all registered agents."""
        registry = AgentRegistry()
        registry.register(MockAgent("agent1"))
        registry.register(MockAgent("agent2"))

        registry.clear()

        assert registry.list_agents() == []

    def test_reset_instance_creates_new_singleton(self):
        """Test that reset_instance creates a new singleton."""
        registry1 = AgentRegistry()
        registry1.register(MockAgent("test"))

        AgentRegistry.reset_instance()
        registry2 = AgentRegistry()

        assert registry1 is not registry2
        assert registry2.list_agents() == []


class TestAgentRegistryEdgeCases:
    """Additional edge case tests for AgentRegistry."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the registry before and after each test."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    def test_register_duplicate_name_overwrites(self):
        """Test that registering with duplicate name overwrites existing."""
        registry = AgentRegistry()
        agent1 = MockAgent("duplicate")
        agent2 = MockAgent("duplicate")

        registry.register(agent1)
        registry.register(agent2)

        assert registry.get("duplicate") is agent2
        assert len(registry.list_agents()) == 1

    def test_get_all_capabilities_with_empty_capabilities(self):
        """Test get_all_capabilities when agent has empty capabilities list."""
        registry = AgentRegistry()
        registry.register(MockAgentNoCapabilities("empty"))

        capabilities = registry.get_all_capabilities()

        assert "empty" in capabilities
        assert capabilities["empty"] == []

    def test_health_check_all_with_mixed_health(self):
        """Test health_check_all with both healthy and unhealthy agents."""
        registry = AgentRegistry()
        registry.register(MockAgent("healthy", healthy=True))
        registry.register(MockAgent("unhealthy", healthy=False))

        health = registry.health_check_all()

        assert health["healthy"] is True
        assert health["unhealthy"] is False

    def test_register_many_agents(self):
        """Test registering many agents."""
        registry = AgentRegistry()
        for i in range(100):
            registry.register(MockAgent(f"agent_{i}"))

        assert len(registry.list_agents()) == 100
        assert registry.get("agent_50") is not None

    def test_get_all_capabilities_with_many_agents(self):
        """Test get_all_capabilities with many registered agents."""
        registry = AgentRegistry()
        for i in range(10):
            registry.register(MockAgent(f"agent_{i}"))

        capabilities = registry.get_all_capabilities()

        assert len(capabilities) == 10
        for i in range(10):
            assert f"agent_{i}" in capabilities


class TestCoreModuleExports:
    """Test that all expected classes are exported from core module."""

    def test_all_classes_importable(self):
        """Test all classes are importable from clarvis_agents.core."""
        from clarvis_agents.core import (
            AgentCapability,
            AgentRegistry,
            AgentResponse,
            BaseAgent,
            ConversationContext,
            ConversationTurn,
        )

        # All imports should have succeeded
        assert AgentResponse is not None
        assert AgentCapability is not None
        assert BaseAgent is not None
        assert ConversationTurn is not None
        assert ConversationContext is not None
        assert AgentRegistry is not None

    def test_all_list_contents(self):
        """Test __all__ contains expected exports."""
        from clarvis_agents import core

        expected = [
            "AgentResponse",
            "AgentCapability",
            "BaseAgent",
            "ConversationTurn",
            "ConversationContext",
            "AgentRegistry",
        ]

        for name in expected:
            assert name in core.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
