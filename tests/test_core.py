"""Tests for core abstractions (Phase 1 - Issue #11)."""

import pytest
from datetime import datetime
from typing import Optional

from clarvis_agents.core import (
    AgentCapability,
    AgentRegistry,
    AgentResponse,
    BaseAgent,
    ConversationContext,
    ConversationTurn,
)


class TestAgentResponse:
    """Test suite for AgentResponse dataclass."""

    def test_response_with_required_fields(self):
        """Test AgentResponse with only required fields."""
        response = AgentResponse(
            content="Hello world",
            success=True,
            agent_name="test_agent",
        )
        assert response.content == "Hello world"
        assert response.success is True
        assert response.agent_name == "test_agent"

    def test_response_defaults_metadata_to_none(self):
        """Test that metadata defaults to None."""
        response = AgentResponse(
            content="Test",
            success=True,
            agent_name="test",
        )
        assert response.metadata is None

    def test_response_defaults_error_to_none(self):
        """Test that error defaults to None."""
        response = AgentResponse(
            content="Test",
            success=True,
            agent_name="test",
        )
        assert response.error is None

    def test_response_with_all_fields(self):
        """Test AgentResponse with all fields specified."""
        response = AgentResponse(
            content="Found 3 emails",
            success=True,
            agent_name="gmail",
            metadata={"email_count": 3},
            error=None,
        )
        assert response.content == "Found 3 emails"
        assert response.success is True
        assert response.agent_name == "gmail"
        assert response.metadata == {"email_count": 3}
        assert response.error is None

    def test_response_failure_case(self):
        """Test AgentResponse for failure case."""
        response = AgentResponse(
            content="",
            success=False,
            agent_name="gmail",
            error="Connection failed",
        )
        assert response.success is False
        assert response.error == "Connection failed"


class TestAgentCapability:
    """Test suite for AgentCapability dataclass."""

    def test_capability_with_all_fields(self):
        """Test AgentCapability with all required fields."""
        capability = AgentCapability(
            name="email_search",
            description="Search emails by sender, subject, or date",
            keywords=["email", "inbox", "mail", "message"],
            examples=["check my unread emails", "find emails from John"],
        )
        assert capability.name == "email_search"
        assert capability.description == "Search emails by sender, subject, or date"
        assert "email" in capability.keywords
        assert len(capability.examples) == 2

    def test_capability_empty_lists(self):
        """Test AgentCapability with empty lists."""
        capability = AgentCapability(
            name="basic",
            description="A basic capability",
            keywords=[],
            examples=[],
        )
        assert capability.keywords == []
        assert capability.examples == []


class TestBaseAgent:
    """Test suite for BaseAgent abstract class."""

    def test_base_agent_cannot_be_instantiated(self):
        """Test that BaseAgent cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore

    def test_concrete_agent_must_implement_all_methods(self):
        """Test that concrete subclass must implement all abstract methods."""

        class IncompleteAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "incomplete"

        # Should raise TypeError because not all abstract methods are implemented
        with pytest.raises(TypeError):
            IncompleteAgent()  # type: ignore

    def test_concrete_agent_can_be_instantiated(self):
        """Test that a properly implemented agent can be instantiated."""

        class TestAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "test_agent"

            @property
            def description(self) -> str:
                return "A test agent"

            @property
            def capabilities(self) -> list[AgentCapability]:
                return [
                    AgentCapability(
                        name="test",
                        description="Test capability",
                        keywords=["test"],
                        examples=["test query"],
                    )
                ]

            async def process(
                self, query: str, context: Optional[ConversationContext] = None
            ) -> AgentResponse:
                return AgentResponse(
                    content=f"Processed: {query}",
                    success=True,
                    agent_name=self.name,
                )

            def health_check(self) -> bool:
                return True

        agent = TestAgent()
        assert agent.name == "test_agent"
        assert agent.description == "A test agent"
        assert len(agent.capabilities) == 1
        assert agent.health_check() is True


class TestConversationTurn:
    """Test suite for ConversationTurn dataclass."""

    def test_turn_with_required_fields(self):
        """Test ConversationTurn with required fields."""
        turn = ConversationTurn(
            query="What's the weather?",
            response="It's sunny today.",
            agent_used="weather",
        )
        assert turn.query == "What's the weather?"
        assert turn.response == "It's sunny today."
        assert turn.agent_used == "weather"

    def test_turn_timestamp_defaults_to_now(self):
        """Test that timestamp defaults to current time."""
        before = datetime.now()
        turn = ConversationTurn(
            query="test",
            response="response",
            agent_used="agent",
        )
        after = datetime.now()

        assert before <= turn.timestamp <= after

    def test_turn_with_explicit_timestamp(self):
        """Test ConversationTurn with explicit timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        turn = ConversationTurn(
            query="test",
            response="response",
            agent_used="agent",
            timestamp=custom_time,
        )
        assert turn.timestamp == custom_time


class TestConversationContext:
    """Test suite for ConversationContext dataclass."""

    def test_context_generates_unique_session_id(self):
        """Test that each context gets a unique session_id."""
        context1 = ConversationContext()
        context2 = ConversationContext()
        assert context1.session_id != context2.session_id

    def test_context_session_id_is_uuid_format(self):
        """Test that session_id is a valid UUID string."""
        context = ConversationContext()
        # UUID format: 8-4-4-4-12 characters
        parts = context.session_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_context_defaults_to_empty_turns(self):
        """Test that turns defaults to empty list."""
        context = ConversationContext()
        assert context.turns == []

    def test_context_defaults_last_agent_to_none(self):
        """Test that last_agent defaults to None."""
        context = ConversationContext()
        assert context.last_agent is None

    def test_add_turn_appends_to_turns(self):
        """Test that add_turn appends a new turn."""
        context = ConversationContext()
        context.add_turn("query1", "response1", "agent1")

        assert len(context.turns) == 1
        assert context.turns[0].query == "query1"
        assert context.turns[0].response == "response1"
        assert context.turns[0].agent_used == "agent1"

    def test_add_turn_updates_last_agent(self):
        """Test that add_turn updates last_agent."""
        context = ConversationContext()
        context.add_turn("query1", "response1", "agent1")
        assert context.last_agent == "agent1"

        context.add_turn("query2", "response2", "agent2")
        assert context.last_agent == "agent2"

    def test_get_recent_context_returns_formatted_string(self):
        """Test get_recent_context returns formatted conversation."""
        context = ConversationContext()
        context.add_turn("Hello", "Hi there!", "assistant")
        context.add_turn("How are you?", "I'm doing well!", "assistant")

        result = context.get_recent_context()

        assert "User: Hello" in result
        assert "Agent (assistant): Hi there!" in result
        assert "User: How are you?" in result
        assert "Agent (assistant): I'm doing well!" in result

    def test_get_recent_context_limits_to_n_turns(self):
        """Test get_recent_context limits to n most recent turns."""
        context = ConversationContext()
        context.add_turn("q1", "r1", "agent")
        context.add_turn("q2", "r2", "agent")
        context.add_turn("q3", "r3", "agent")
        context.add_turn("q4", "r4", "agent")

        result = context.get_recent_context(n=2)

        assert "User: q1" not in result
        assert "User: q2" not in result
        assert "User: q3" in result
        assert "User: q4" in result

    def test_get_recent_context_with_empty_turns(self):
        """Test get_recent_context with no turns."""
        context = ConversationContext()
        result = context.get_recent_context()
        assert result == ""

    def test_should_continue_with_agent_returns_none_when_no_history(self):
        """Test follow-up detection returns None with no history."""
        context = ConversationContext()
        assert context.should_continue_with_agent("what about email?") is None

    def test_should_continue_with_agent_detects_follow_up_phrases(self):
        """Test follow-up detection for common follow-up phrases."""
        context = ConversationContext()
        context.add_turn("Check my email", "You have 3 emails", "gmail")

        follow_up_queries = [
            "what about unread ones?",
            "and also from John",
            "also check spam",
            "more about the first one",
            "tell me more",
            "can you show details?",
            "what else is there?",
            "anything else?",
        ]

        for query in follow_up_queries:
            result = context.should_continue_with_agent(query)
            assert result == "gmail", f"Failed for query: {query}"

    def test_should_continue_with_agent_detects_pronouns(self):
        """Test follow-up detection for short queries with pronouns."""
        context = ConversationContext()
        context.add_turn("Check my email", "You have 3 emails", "gmail")

        pronoun_queries = [
            "read it",
            "show them",
            "what's that?",
            "those ones",
            "this email",
        ]

        for query in pronoun_queries:
            result = context.should_continue_with_agent(query)
            assert result == "gmail", f"Failed for query: {query}"

    def test_should_continue_with_agent_returns_none_for_new_topics(self):
        """Test follow-up detection returns None for clearly new topics."""
        context = ConversationContext()
        context.add_turn("Check my email", "You have 3 emails", "gmail")

        new_topic_queries = [
            "What's the weather today?",
            "Set a reminder for tomorrow",
            "Play some music",
            "Search for restaurants nearby",
        ]

        for query in new_topic_queries:
            result = context.should_continue_with_agent(query)
            assert result is None, f"Should not follow-up for: {query}"


class TestAgentRegistry:
    """Test suite for AgentRegistry singleton."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the registry before and after each test."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    def _create_mock_agent(self, name: str) -> BaseAgent:
        """Helper to create a mock agent for testing."""

        class MockAgent(BaseAgent):
            def __init__(self, agent_name: str):
                self._name = agent_name

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
                return True

        return MockAgent(name)

    def test_registry_is_singleton(self):
        """Test that AgentRegistry returns the same instance."""
        registry1 = AgentRegistry()
        registry2 = AgentRegistry()
        assert registry1 is registry2

    def test_register_adds_agent(self):
        """Test that register adds an agent to the registry."""
        registry = AgentRegistry()
        agent = self._create_mock_agent("test")

        registry.register(agent)

        assert registry.get("test") is agent

    def test_get_returns_registered_agent(self):
        """Test that get returns a registered agent."""
        registry = AgentRegistry()
        agent = self._create_mock_agent("test")
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
        registry.register(self._create_mock_agent("agent1"))
        registry.register(self._create_mock_agent("agent2"))
        registry.register(self._create_mock_agent("agent3"))

        names = registry.list_agents()

        assert set(names) == {"agent1", "agent2", "agent3"}

    def test_list_agents_empty_registry(self):
        """Test list_agents with empty registry."""
        registry = AgentRegistry()
        assert registry.list_agents() == []

    def test_unregister_removes_agent(self):
        """Test that unregister removes an agent."""
        registry = AgentRegistry()
        agent = self._create_mock_agent("test")
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
        registry.register(self._create_mock_agent("agent1"))
        registry.register(self._create_mock_agent("agent2"))

        capabilities = registry.get_all_capabilities()

        assert "agent1" in capabilities
        assert "agent2" in capabilities
        assert len(capabilities["agent1"]) == 1
        assert capabilities["agent1"][0].name == "agent1_cap"

    def test_health_check_all_returns_dict(self):
        """Test that health_check_all returns health status dict."""
        registry = AgentRegistry()
        registry.register(self._create_mock_agent("agent1"))
        registry.register(self._create_mock_agent("agent2"))

        health = registry.health_check_all()

        assert health == {"agent1": True, "agent2": True}

    def test_clear_removes_all_agents(self):
        """Test that clear removes all registered agents."""
        registry = AgentRegistry()
        registry.register(self._create_mock_agent("agent1"))
        registry.register(self._create_mock_agent("agent2"))

        registry.clear()

        assert registry.list_agents() == []

    def test_reset_instance_creates_new_singleton(self):
        """Test that reset_instance creates a new singleton."""
        registry1 = AgentRegistry()
        registry1.register(self._create_mock_agent("test"))

        AgentRegistry.reset_instance()
        registry2 = AgentRegistry()

        assert registry1 is not registry2
        assert registry2.list_agents() == []


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
