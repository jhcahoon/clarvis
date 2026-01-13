"""Tests for OrchestratorAgent and OrchestratorConfig (Issue #18)."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
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
    load_config,
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


# ============================================================================
# OrchestratorConfig Tests
# ============================================================================


class TestOrchestratorConfig:
    """Test suite for OrchestratorConfig dataclass."""

    def test_config_defaults(self):
        """Test configuration defaults."""
        config = OrchestratorConfig()

        # Orchestrator settings
        assert config.model == "claude-sonnet-4-20250514"
        assert config.router_model == "claude-3-5-haiku-20241022"
        assert config.session_timeout_minutes == 30
        assert config.max_turns == 5

        # Routing settings
        assert config.code_routing_threshold == 0.7
        assert config.llm_routing_enabled is True
        assert config.follow_up_detection is True
        assert config.default_agent is None

        # Agent settings
        assert config.enabled_agents == {"gmail": True}
        assert config.agent_priorities == {"gmail": 1}

        # Logging settings
        assert config.log_level == "INFO"
        assert config.log_routing_decisions is True
        assert config.log_agent_responses is True

    def test_config_custom_values(self):
        """Test configuration with custom values."""
        config = OrchestratorConfig(
            model="claude-opus-4-20250514",
            router_model="claude-3-haiku-20240307",
            session_timeout_minutes=60,
            max_turns=10,
            code_routing_threshold=0.8,
            llm_routing_enabled=False,
            follow_up_detection=False,
            default_agent="gmail",
            enabled_agents={"gmail": True, "calendar": True},
            agent_priorities={"gmail": 1, "calendar": 2},
            log_level="DEBUG",
            log_routing_decisions=False,
            log_agent_responses=False,
        )

        assert config.model == "claude-opus-4-20250514"
        assert config.router_model == "claude-3-haiku-20240307"
        assert config.session_timeout_minutes == 60
        assert config.max_turns == 10
        assert config.code_routing_threshold == 0.8
        assert config.llm_routing_enabled is False
        assert config.follow_up_detection is False
        assert config.default_agent == "gmail"
        assert config.enabled_agents == {"gmail": True, "calendar": True}
        assert config.agent_priorities == {"gmail": 1, "calendar": 2}
        assert config.log_level == "DEBUG"
        assert config.log_routing_decisions is False
        assert config.log_agent_responses is False

    def test_config_threshold_range(self):
        """Test that threshold can be set to boundary values."""
        config_zero = OrchestratorConfig(code_routing_threshold=0.0)
        assert config_zero.code_routing_threshold == 0.0

        config_one = OrchestratorConfig(code_routing_threshold=1.0)
        assert config_one.code_routing_threshold == 1.0

    def test_from_file_missing_returns_defaults(self):
        """Test that from_file returns defaults when file is missing."""
        non_existent_path = Path("/non/existent/path/config.json")
        config = OrchestratorConfig.from_file(non_existent_path)

        assert config.model == "claude-sonnet-4-20250514"
        assert config.router_model == "claude-3-5-haiku-20241022"

    def test_from_file_loads_values(self):
        """Test that from_file loads values from JSON."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(
                {
                    "model": "custom-model",
                    "router_model": "custom-router",
                    "session_timeout_minutes": 45,
                    "code_routing_threshold": 0.5,
                    "llm_routing_enabled": False,
                    "follow_up_detection": False,
                },
                f,
            )
            temp_path = Path(f.name)

        try:
            config = OrchestratorConfig.from_file(temp_path)

            assert config.model == "custom-model"
            assert config.router_model == "custom-router"
            assert config.session_timeout_minutes == 45
            assert config.code_routing_threshold == 0.5
            assert config.llm_routing_enabled is False
            assert config.follow_up_detection is False
        finally:
            temp_path.unlink()

    def test_from_file_partial_json(self):
        """Test that from_file handles partial JSON with defaults."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"model": "partial-model"}, f)
            temp_path = Path(f.name)

        try:
            config = OrchestratorConfig.from_file(temp_path)

            # Custom value
            assert config.model == "partial-model"
            # Defaults for missing values
            assert config.router_model == "claude-3-5-haiku-20241022"
            assert config.session_timeout_minutes == 30
            assert config.code_routing_threshold == 0.7
        finally:
            temp_path.unlink()

    def test_from_file_corrupted_json_returns_defaults(self):
        """Test that from_file returns defaults for corrupted JSON."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{ invalid json content }")
            temp_path = Path(f.name)

        try:
            config = OrchestratorConfig.from_file(temp_path)

            # Should return defaults, not crash
            assert config.model == "claude-sonnet-4-20250514"
            assert config.router_model == "claude-3-5-haiku-20241022"
        finally:
            temp_path.unlink()

    def test_default_config_path(self):
        """Test that default_config_path returns expected path."""
        path = OrchestratorConfig.default_config_path()

        assert path.name == "orchestrator_config.json"
        assert "configs" in str(path)

    def test_load_config_helper(self):
        """Test the load_config helper function."""
        config = load_config()

        # Should return a valid config (either from file or defaults)
        assert isinstance(config, OrchestratorConfig)
        assert config.model is not None

    def test_from_file_nested_structure(self):
        """Test that from_file correctly parses nested JSON structure."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(
                {
                    "orchestrator": {
                        "model": "claude-opus-4-20250514",
                        "router_model": "claude-3-haiku-20240307",
                        "session_timeout_minutes": 45,
                        "max_turns": 10,
                    },
                    "routing": {
                        "code_routing_threshold": 0.8,
                        "llm_routing_enabled": False,
                        "follow_up_detection": False,
                        "default_agent": "gmail",
                    },
                    "agents": {
                        "gmail": {"enabled": True, "priority": 1},
                        "calendar": {"enabled": True, "priority": 2},
                        "weather": {"enabled": False, "priority": 3},
                    },
                    "logging": {
                        "level": "DEBUG",
                        "log_routing_decisions": False,
                        "log_agent_responses": True,
                    },
                },
                f,
            )
            temp_path = Path(f.name)

        try:
            config = OrchestratorConfig.from_file(temp_path)

            # Orchestrator settings
            assert config.model == "claude-opus-4-20250514"
            assert config.router_model == "claude-3-haiku-20240307"
            assert config.session_timeout_minutes == 45
            assert config.max_turns == 10

            # Routing settings
            assert config.code_routing_threshold == 0.8
            assert config.llm_routing_enabled is False
            assert config.follow_up_detection is False
            assert config.default_agent == "gmail"

            # Agent settings
            assert config.enabled_agents == {
                "gmail": True,
                "calendar": True,
                "weather": False,
            }
            assert config.agent_priorities == {
                "gmail": 1,
                "calendar": 2,
                "weather": 3,
            }

            # Logging settings
            assert config.log_level == "DEBUG"
            assert config.log_routing_decisions is False
            assert config.log_agent_responses is True
        finally:
            temp_path.unlink()

    def test_from_file_nested_partial(self):
        """Test nested structure with missing sections uses defaults."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            # Only include orchestrator section, others should default
            json.dump(
                {
                    "orchestrator": {
                        "model": "custom-model",
                    },
                },
                f,
            )
            temp_path = Path(f.name)

        try:
            config = OrchestratorConfig.from_file(temp_path)

            # Custom value from orchestrator section
            assert config.model == "custom-model"
            # Defaults for missing orchestrator fields
            assert config.router_model == "claude-3-5-haiku-20241022"
            assert config.session_timeout_minutes == 30
            assert config.max_turns == 5

            # Defaults for missing routing section
            assert config.code_routing_threshold == 0.7
            assert config.llm_routing_enabled is True
            assert config.follow_up_detection is True
            assert config.default_agent is None

            # Defaults for missing agents section
            assert config.enabled_agents == {"gmail": True}
            assert config.agent_priorities == {"gmail": 1}

            # Defaults for missing logging section
            assert config.log_level == "INFO"
            assert config.log_routing_decisions is True
            assert config.log_agent_responses is True
        finally:
            temp_path.unlink()

    def test_from_file_agents_section_empty(self):
        """Test that empty agents section uses defaults."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(
                {
                    "orchestrator": {"model": "custom-model"},
                    "agents": {},  # Empty agents section
                },
                f,
            )
            temp_path = Path(f.name)

        try:
            config = OrchestratorConfig.from_file(temp_path)
            # Should use defaults when agents section is empty
            assert config.enabled_agents == {"gmail": True}
            assert config.agent_priorities == {"gmail": 1}
        finally:
            temp_path.unlink()

    def test_backward_compatibility_flat_config(self):
        """Test that flat (legacy) config format still works."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            # Flat structure (no nested sections)
            json.dump(
                {
                    "model": "legacy-model",
                    "router_model": "legacy-router",
                    "session_timeout_minutes": 20,
                    "code_routing_threshold": 0.6,
                    "llm_routing_enabled": False,
                    "follow_up_detection": False,
                },
                f,
            )
            temp_path = Path(f.name)

        try:
            config = OrchestratorConfig.from_file(temp_path)

            # Values from flat config
            assert config.model == "legacy-model"
            assert config.router_model == "legacy-router"
            assert config.session_timeout_minutes == 20
            assert config.code_routing_threshold == 0.6
            assert config.llm_routing_enabled is False
            assert config.follow_up_detection is False

            # Defaults for new fields not in flat config
            assert config.max_turns == 5
            assert config.default_agent is None
            assert config.enabled_agents == {"gmail": True}
            assert config.agent_priorities == {"gmail": 1}
            assert config.log_level == "INFO"
            assert config.log_routing_decisions is True
            assert config.log_agent_responses is True
        finally:
            temp_path.unlink()


# ============================================================================
# OrchestratorAgent Tests
# ============================================================================


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


class TestOrchestratorAgentEdgeCases:
    """Additional edge case tests for OrchestratorAgent."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry between tests."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    def test_cleanup_expired_sessions_multiple(self):
        """Test cleanup with multiple expired and active sessions."""
        registry = AgentRegistry()
        config = OrchestratorConfig(session_timeout_minutes=1)
        orchestrator = OrchestratorAgent(config, registry)

        # Create multiple sessions
        for i in range(5):
            orchestrator.get_or_create_session(f"session-{i}")

        # Expire some sessions
        now = datetime.now()
        orchestrator._session_timestamps["session-0"] = now - timedelta(minutes=5)
        orchestrator._session_timestamps["session-1"] = now - timedelta(minutes=5)
        orchestrator._session_timestamps["session-2"] = now - timedelta(minutes=5)
        # session-3 and session-4 remain active

        # Trigger cleanup
        orchestrator.get_or_create_session("new-session")

        # Verify expired sessions removed
        assert "session-0" not in orchestrator._sessions
        assert "session-1" not in orchestrator._sessions
        assert "session-2" not in orchestrator._sessions
        assert "session-3" in orchestrator._sessions
        assert "session-4" in orchestrator._sessions

    def test_get_client_caches_instance(self):
        """Test that _get_client caches the Anthropic client."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        orchestrator = OrchestratorAgent(config, registry)

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("clarvis_agents.orchestrator.agent.Anthropic") as mock_anthropic:
                mock_client = MagicMock()
                mock_anthropic.return_value = mock_client

                client1 = orchestrator._get_client()
                client2 = orchestrator._get_client()

                # Should only create client once
                assert mock_anthropic.call_count == 1
                assert client1 is client2


class TestSessionContinuity:
    """Test session continuity across multiple queries."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry between tests."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    @pytest.mark.asyncio
    async def test_session_maintains_context(self):
        """Test that session context is maintained across queries."""
        registry = AgentRegistry()
        config = OrchestratorConfig()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_client.messages.create.return_value = mock_response

        orchestrator = OrchestratorAgent(
            config, registry, anthropic_client=mock_client
        )

        # First query
        await orchestrator.process("hello", session_id="test-session")

        # Second query in same session
        await orchestrator.process("hi again", session_id="test-session")

        # Verify context has both turns
        context = orchestrator._sessions["test-session"]
        assert len(context.turns) == 2

    @pytest.mark.asyncio
    async def test_different_sessions_isolated(self):
        """Test that different sessions are isolated from each other."""
        registry = AgentRegistry()
        config = OrchestratorConfig()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_client.messages.create.return_value = mock_response

        orchestrator = OrchestratorAgent(
            config, registry, anthropic_client=mock_client
        )

        # Query in session A
        await orchestrator.process("hello", session_id="session-a")

        # Query in session B
        await orchestrator.process("hi", session_id="session-b")

        # Verify sessions are separate
        assert len(orchestrator._sessions["session-a"].turns) == 1
        assert len(orchestrator._sessions["session-b"].turns) == 1
        assert orchestrator._sessions["session-a"].turns[0].query == "hello"
        assert orchestrator._sessions["session-b"].turns[0].query == "hi"


class TestModuleExports:
    """Test suite for module exports."""

    def test_all_classes_importable(self):
        """Test all new classes are importable from orchestrator module."""
        from clarvis_agents.orchestrator import (
            OrchestratorAgent,
            OrchestratorConfig,
            create_orchestrator,
            load_config,
        )

        assert OrchestratorAgent is not None
        assert OrchestratorConfig is not None
        assert create_orchestrator is not None
        assert load_config is not None

    def test_all_list_contains_new_exports(self):
        """Test __all__ contains new exports."""
        from clarvis_agents import orchestrator

        assert "OrchestratorAgent" in orchestrator.__all__
        assert "OrchestratorConfig" in orchestrator.__all__
        assert "create_orchestrator" in orchestrator.__all__
        assert "load_config" in orchestrator.__all__


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
