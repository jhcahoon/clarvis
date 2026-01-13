"""Tests for OrchestratorAgent (Phase 4 - Issue #14)."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from clarvis_agents.core import (
    AgentCapability,
    AgentRegistry,
    AgentResponse,
    BaseAgent,
    ConversationContext,
)
from clarvis_agents.orchestrator import (
    OrchestratorAgent,
    OrchestratorConfig,
    RoutingDecision,
    create_orchestrator,
)


class MockAgent(BaseAgent):
    """Mock agent for testing orchestrator delegation."""

    def __init__(self, name: str = "mock_agent", should_fail: bool = False):
        self._name = name
        self._should_fail = should_fail

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
                name="mock_capability",
                description="A mock capability for testing",
                keywords=["mock", "test"],
                examples=["test query"],
            )
        ]

    async def process(
        self, query: str, context: ConversationContext | None = None
    ) -> AgentResponse:
        if self._should_fail:
            raise RuntimeError("Mock agent failure")
        return AgentResponse(
            content=f"Mock response to: {query}",
            success=True,
            agent_name=self.name,
        )

    def health_check(self) -> bool:
        return not self._should_fail


class TestOrchestratorAgentInit:
    """Test suite for OrchestratorAgent initialization."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry between tests."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    def test_is_base_agent(self):
        """Test OrchestratorAgent is a BaseAgent."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        assert isinstance(orchestrator, BaseAgent)

    def test_properties(self):
        """Test OrchestratorAgent properties return expected values."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        assert orchestrator.name == "orchestrator"
        assert "coordinator" in orchestrator.description.lower()
        assert len(orchestrator.capabilities) >= 1

    def test_capabilities_structure(self):
        """Test capabilities have required fields."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        for cap in orchestrator.capabilities:
            assert isinstance(cap, AgentCapability)
            assert cap.name
            assert cap.description
            assert isinstance(cap.keywords, list)
            assert isinstance(cap.examples, list)

    def test_health_check_with_healthy_agents(self):
        """Test health_check returns True with healthy agents."""
        registry = AgentRegistry()
        registry.register(MockAgent("test"))
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        assert orchestrator.health_check() is True

    def test_health_check_with_no_agents(self):
        """Test health_check returns True with empty registry."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        assert orchestrator.health_check() is True

    def test_health_check_with_unhealthy_agents(self):
        """Test health_check returns False when all agents are unhealthy."""
        registry = AgentRegistry()
        registry.register(MockAgent("test", should_fail=True))
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        assert orchestrator.health_check() is False


class TestSessionManagement:
    """Test suite for session management."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry between tests."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    def test_create_new_session(self):
        """Test get_or_create_session creates new session when none exists."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        context = orchestrator.get_or_create_session()

        assert context is not None
        assert context.session_id in orchestrator._sessions

    def test_create_session_with_custom_id(self):
        """Test creating session with custom session_id."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        context = orchestrator.get_or_create_session("custom-session-id")

        assert context.session_id == "custom-session-id"
        assert "custom-session-id" in orchestrator._sessions

    def test_get_existing_session(self):
        """Test get_or_create_session returns existing session."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        # Create session
        context1 = orchestrator.get_or_create_session("test-session")
        context1.add_turn("query", "response", "agent")

        # Get same session
        context2 = orchestrator.get_or_create_session("test-session")

        assert context1 is context2
        assert len(context2.turns) == 1

    def test_cleanup_expired(self):
        """Test expired sessions are cleaned up."""
        registry = AgentRegistry()
        config = OrchestratorConfig(session_timeout_minutes=1)
        orchestrator = OrchestratorAgent(config, registry)

        # Create session
        context = orchestrator.get_or_create_session("old-session")

        # Manually expire the session
        orchestrator._session_timestamps["old-session"] = datetime.now() - timedelta(
            minutes=5
        )

        # Trigger cleanup by creating new session
        orchestrator.get_or_create_session("new-session")

        assert "old-session" not in orchestrator._sessions

    def test_session_timestamp_updated_on_access(self):
        """Test session timestamp is updated when session is accessed."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        # Create session
        orchestrator.get_or_create_session("test-session")
        initial_timestamp = orchestrator._session_timestamps["test-session"]

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        # Access session again
        orchestrator.get_or_create_session("test-session")
        updated_timestamp = orchestrator._session_timestamps["test-session"]

        assert updated_timestamp >= initial_timestamp


class TestHandlerMethods:
    """Test suite for handler methods."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry between tests."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    @pytest.mark.asyncio
    async def test_handle_direct_success(self):
        """Test _handle_direct returns AgentResponse with mocked client."""
        registry = AgentRegistry()
        config = OrchestratorConfig()

        # Mock Anthropic client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello! How can I help?")]
        mock_client.messages.create.return_value = mock_response

        orchestrator = OrchestratorAgent(
            config, registry, anthropic_client=mock_client
        )
        context = ConversationContext()

        response = await orchestrator._handle_direct("hello", context)

        assert response.success is True
        assert response.agent_name == "orchestrator"
        assert response.content == "Hello! How can I help?"
        assert response.metadata.get("handled_directly") is True

    @pytest.mark.asyncio
    async def test_handle_direct_with_context(self):
        """Test _handle_direct includes recent context in prompt."""
        registry = AgentRegistry()
        config = OrchestratorConfig()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_client.messages.create.return_value = mock_response

        orchestrator = OrchestratorAgent(
            config, registry, anthropic_client=mock_client
        )

        # Create context with history
        context = ConversationContext()
        context.add_turn("previous query", "previous response", "agent")

        await orchestrator._handle_direct("new query", context)

        # Verify the message includes context
        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        assert "Recent conversation" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_handle_direct_error(self):
        """Test _handle_direct handles errors gracefully."""
        registry = AgentRegistry()
        config = OrchestratorConfig()

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API Error")

        orchestrator = OrchestratorAgent(
            config, registry, anthropic_client=mock_client
        )
        context = ConversationContext()

        response = await orchestrator._handle_direct("hello", context)

        # Should return fallback response, not raise exception
        assert response.success is True
        assert response.metadata.get("fallback") is True

    @pytest.mark.asyncio
    async def test_handle_single_agent_success(self):
        """Test _handle_single_agent successfully delegates to agent."""
        registry = AgentRegistry()
        mock_agent = MockAgent("test_agent")
        registry.register(mock_agent)

        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        decision = RoutingDecision(
            agent_name="test_agent",
            confidence=0.9,
            reasoning="Test routing",
            handle_directly=False,
        )
        context = ConversationContext()

        response = await orchestrator._handle_single_agent(
            "test query", decision, context
        )

        assert response.success is True
        assert response.agent_name == "test_agent"
        assert "test query" in response.content

    @pytest.mark.asyncio
    async def test_handle_single_agent_not_found(self):
        """Test _handle_single_agent falls back when agent not found."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        decision = RoutingDecision(
            agent_name="nonexistent_agent",
            confidence=0.9,
            reasoning="Test routing",
            handle_directly=False,
        )
        context = ConversationContext()

        response = await orchestrator._handle_single_agent(
            "test query", decision, context
        )

        # Should fallback to fallback handler
        assert response.agent_name == "orchestrator"
        assert response.metadata.get("fallback") is True

    @pytest.mark.asyncio
    async def test_handle_single_agent_error(self):
        """Test _handle_single_agent handles agent errors gracefully."""
        registry = AgentRegistry()
        mock_agent = MockAgent("failing_agent", should_fail=True)
        registry.register(mock_agent)

        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        decision = RoutingDecision(
            agent_name="failing_agent",
            confidence=0.9,
            reasoning="Test routing",
            handle_directly=False,
        )
        context = ConversationContext()

        response = await orchestrator._handle_single_agent(
            "test query", decision, context
        )

        assert response.success is False
        assert "error" in response.error.lower() or "failure" in response.error.lower()

    @pytest.mark.asyncio
    async def test_handle_fallback_lists_agents(self):
        """Test _handle_fallback lists available agents."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail"))
        registry.register(MockAgent("calendar"))

        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)
        context = ConversationContext()

        response = await orchestrator._handle_fallback("unknown query", context)

        assert response.success is True
        assert "gmail" in response.content.lower()
        assert "calendar" in response.content.lower()
        assert response.metadata.get("fallback") is True

    @pytest.mark.asyncio
    async def test_handle_fallback_empty_registry(self):
        """Test _handle_fallback works with empty registry."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)
        context = ConversationContext()

        response = await orchestrator._handle_fallback("unknown query", context)

        assert response.success is True
        assert "rephras" in response.content.lower()


class TestProcessMethod:
    """Test suite for process() method."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry between tests."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    @pytest.mark.asyncio
    async def test_process_routes_greeting(self):
        """Test process routes greeting to direct handler."""
        registry = AgentRegistry()
        config = OrchestratorConfig()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello!")]
        mock_client.messages.create.return_value = mock_response

        orchestrator = OrchestratorAgent(
            config, registry, anthropic_client=mock_client
        )

        response = await orchestrator.process("hello")

        assert response.success is True
        assert response.agent_name == "orchestrator"
        assert response.metadata.get("handled_directly") is True

    @pytest.mark.asyncio
    async def test_process_routes_to_agent(self):
        """Test process routes email query to mock Gmail agent."""
        registry = AgentRegistry()
        mock_gmail = MockAgent("gmail")
        registry.register(mock_gmail)

        config = OrchestratorConfig(llm_routing_enabled=False)
        orchestrator = OrchestratorAgent(config, registry)

        response = await orchestrator.process("check my emails")

        assert response.success is True
        assert response.agent_name == "gmail"

    @pytest.mark.asyncio
    async def test_process_updates_context(self):
        """Test process updates context after processing."""
        registry = AgentRegistry()
        config = OrchestratorConfig()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_client.messages.create.return_value = mock_response

        orchestrator = OrchestratorAgent(
            config, registry, anthropic_client=mock_client
        )

        context = ConversationContext()
        await orchestrator.process("hello", context=context)

        assert len(context.turns) == 1
        assert context.turns[0].query == "hello"
        assert context.last_agent == "orchestrator"

    @pytest.mark.asyncio
    async def test_process_handles_error(self):
        """Test process handles routing errors gracefully."""
        registry = AgentRegistry()
        config = OrchestratorConfig()

        # Create orchestrator with a router that will fail
        orchestrator = OrchestratorAgent(config, registry)

        # Mock router to raise exception
        mock_router = AsyncMock()
        mock_router.route.side_effect = RuntimeError("Router error")
        orchestrator._router = mock_router

        response = await orchestrator.process("test query")

        assert response.success is False
        assert "error" in response.content.lower()

    @pytest.mark.asyncio
    async def test_process_with_session_id(self):
        """Test process creates/uses session from session_id."""
        registry = AgentRegistry()
        config = OrchestratorConfig()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_client.messages.create.return_value = mock_response

        orchestrator = OrchestratorAgent(
            config, registry, anthropic_client=mock_client
        )

        # First call creates session
        await orchestrator.process("hello", session_id="my-session")
        assert "my-session" in orchestrator._sessions

        # Second call uses same session
        await orchestrator.process("hi again", session_id="my-session")
        context = orchestrator._sessions["my-session"]
        assert len(context.turns) == 2


class TestCreateOrchestrator:
    """Test suite for create_orchestrator factory."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry between tests."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    def test_create_with_defaults(self):
        """Test factory creates orchestrator with default config."""
        orchestrator = create_orchestrator()

        assert orchestrator is not None
        assert isinstance(orchestrator, OrchestratorAgent)
        assert orchestrator.name == "orchestrator"

    def test_create_with_custom_config(self):
        """Test factory creates orchestrator with custom config."""
        config = OrchestratorConfig(
            session_timeout_minutes=60,
            code_routing_threshold=0.8,
        )

        orchestrator = create_orchestrator(config)

        assert orchestrator._config.session_timeout_minutes == 60
        assert orchestrator._config.code_routing_threshold == 0.8


class TestModuleExports:
    """Test suite for module exports."""

    def test_all_classes_importable(self):
        """Test all new classes are importable from orchestrator module."""
        from clarvis_agents.orchestrator import (
            OrchestratorAgent,
            create_orchestrator,
        )

        assert OrchestratorAgent is not None
        assert create_orchestrator is not None

    def test_all_list_contains_new_exports(self):
        """Test __all__ contains new exports."""
        from clarvis_agents import orchestrator

        assert "OrchestratorAgent" in orchestrator.__all__
        assert "create_orchestrator" in orchestrator.__all__


class TestBaseAgentInterface:
    """Test suite for BaseAgent interface compliance."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry between tests."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    def test_orchestrator_is_base_agent(self):
        """Test OrchestratorAgent is a BaseAgent subclass."""
        assert issubclass(OrchestratorAgent, BaseAgent)

    def test_all_abstract_methods_implemented(self):
        """Test all BaseAgent abstract methods are implemented."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        # These should not raise NotImplementedError
        _ = orchestrator.name
        _ = orchestrator.description
        _ = orchestrator.capabilities
        _ = orchestrator.health_check()

    @pytest.mark.asyncio
    async def test_process_returns_agent_response(self):
        """Test process returns AgentResponse."""
        registry = AgentRegistry()
        config = OrchestratorConfig()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_client.messages.create.return_value = mock_response

        orchestrator = OrchestratorAgent(
            config, registry, anthropic_client=mock_client
        )

        response = await orchestrator.process("hello")

        assert isinstance(response, AgentResponse)
        assert response.content
        assert isinstance(response.success, bool)
        assert response.agent_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
