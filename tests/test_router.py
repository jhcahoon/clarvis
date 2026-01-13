"""Tests for IntentRouter (Phase 3 - Issue #13)."""

import pytest
from unittest.mock import MagicMock, patch

from clarvis_agents.core import (
    AgentCapability,
    AgentRegistry,
    AgentResponse,
    BaseAgent,
    ConversationContext,
)
from clarvis_agents.orchestrator import (
    ClassificationResult,
    IntentClassifier,
    IntentRouter,
    OrchestratorConfig,
    RoutingDecision,
)
from clarvis_agents.orchestrator.prompts import (
    GREETING_PATTERNS,
    ROUTER_SYSTEM_PROMPT,
    THANKS_PATTERNS,
    format_agent_descriptions,
)


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    def __init__(self, name: str, description: str = "Mock agent"):
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="test_capability",
                description=f"Test capability for {self._name}",
                keywords=["test"],
                examples=["test query 1", "test query 2"],
            )
        ]

    async def process(
        self, query: str, context: ConversationContext | None = None
    ) -> AgentResponse:
        return AgentResponse(
            content=f"Response from {self._name}",
            success=True,
            agent_name=self._name,
        )

    def health_check(self) -> bool:
        return True


class TestRoutingDecision:
    """Test suite for RoutingDecision dataclass."""

    def test_routing_decision_with_required_fields(self):
        """Test RoutingDecision with required fields."""
        decision = RoutingDecision(
            agent_name="gmail",
            confidence=0.8,
            reasoning="Test reasoning",
        )
        assert decision.agent_name == "gmail"
        assert decision.confidence == 0.8
        assert decision.reasoning == "Test reasoning"
        assert decision.handle_directly is False

    def test_routing_decision_with_handle_directly_true(self):
        """Test RoutingDecision with handle_directly=True."""
        decision = RoutingDecision(
            agent_name=None,
            confidence=1.0,
            reasoning="Greeting detected",
            handle_directly=True,
        )
        assert decision.agent_name is None
        assert decision.handle_directly is True

    def test_routing_decision_with_none_agent_name(self):
        """Test RoutingDecision with None agent_name."""
        decision = RoutingDecision(
            agent_name=None,
            confidence=0.0,
            reasoning="No match found",
        )
        assert decision.agent_name is None
        assert decision.handle_directly is False

    def test_routing_decision_confidence_bounds(self):
        """Test confidence can be set to boundary values."""
        decision_zero = RoutingDecision(
            agent_name=None,
            confidence=0.0,
            reasoning="Zero confidence",
        )
        assert decision_zero.confidence == 0.0

        decision_one = RoutingDecision(
            agent_name="gmail",
            confidence=1.0,
            reasoning="Full confidence",
        )
        assert decision_one.confidence == 1.0


class TestRouterPrompts:
    """Test suite for router prompts."""

    def test_router_system_prompt_has_placeholder(self):
        """Test that ROUTER_SYSTEM_PROMPT has agent_descriptions placeholder."""
        assert "{agent_descriptions}" in ROUTER_SYSTEM_PROMPT

    def test_greeting_patterns_contains_expected_phrases(self):
        """Test that GREETING_PATTERNS contains expected greetings."""
        expected = ["hello", "hi", "hey", "good morning"]
        for phrase in expected:
            assert phrase in GREETING_PATTERNS

    def test_thanks_patterns_contains_expected_phrases(self):
        """Test that THANKS_PATTERNS contains expected phrases."""
        expected = ["thank you", "thanks", "thx"]
        for phrase in expected:
            assert phrase in THANKS_PATTERNS

    def test_format_agent_descriptions_empty(self):
        """Test format_agent_descriptions with empty dict."""
        result = format_agent_descriptions({})
        assert "No agents" in result

    def test_format_agent_descriptions_single_agent(self):
        """Test format_agent_descriptions with single agent."""
        capabilities = {
            "gmail": [
                AgentCapability(
                    name="email_check",
                    description="Check emails",
                    keywords=["email"],
                    examples=["check my email", "read inbox"],
                )
            ]
        }
        result = format_agent_descriptions(capabilities)

        assert "Agent: gmail" in result
        assert "email_check" in result
        assert "Check emails" in result
        assert "check my email" in result

    def test_format_agent_descriptions_multiple_agents(self):
        """Test format_agent_descriptions with multiple agents."""
        capabilities = {
            "gmail": [
                AgentCapability(
                    name="email_check",
                    description="Check emails",
                    keywords=["email"],
                    examples=["check my email"],
                )
            ],
            "calendar": [
                AgentCapability(
                    name="calendar_check",
                    description="Check calendar",
                    keywords=["calendar"],
                    examples=["check my schedule"],
                )
            ],
        }
        result = format_agent_descriptions(capabilities)

        assert "Agent: gmail" in result
        assert "Agent: calendar" in result

    def test_format_agent_descriptions_no_capabilities(self):
        """Test format_agent_descriptions with agent having no capabilities."""
        capabilities = {"empty_agent": []}
        result = format_agent_descriptions(capabilities)

        assert "Agent: empty_agent" in result
        assert "No capabilities defined" in result


class TestIntentRouterInit:
    """Test suite for IntentRouter initialization."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the registry before and after each test."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    def test_init_with_required_args(self):
        """Test IntentRouter initialization with required args."""
        registry = AgentRegistry()
        config = OrchestratorConfig()

        router = IntentRouter(registry, config)

        assert router.registry is registry
        assert router.config is config
        assert router.classifier is not None

    def test_init_uses_config_threshold(self):
        """Test that router uses threshold from config."""
        registry = AgentRegistry()
        config = OrchestratorConfig(code_routing_threshold=0.5)

        router = IntentRouter(registry, config)

        assert router.classifier.threshold == 0.5

    def test_init_with_custom_classifier(self):
        """Test IntentRouter with custom classifier injection."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        custom_classifier = IntentClassifier(threshold=0.3)

        router = IntentRouter(registry, config, classifier=custom_classifier)

        assert router.classifier is custom_classifier
        assert router.classifier.threshold == 0.3

    def test_init_with_custom_anthropic_client(self):
        """Test IntentRouter with custom Anthropic client injection."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        mock_client = MagicMock()

        router = IntentRouter(registry, config, anthropic_client=mock_client)

        assert router._client is mock_client
        assert router.client is mock_client

    def test_client_raises_error_when_api_key_missing(self):
        """Test that accessing client raises ValueError when API key not set."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        router = IntentRouter(registry, config)

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                _ = router.client


class TestDirectHandling:
    """Test suite for _should_handle_directly."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the registry before and after each test."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    @pytest.fixture
    def router(self):
        """Create a router instance for testing."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        return IntentRouter(registry, config)

    def test_greeting_hello_detected(self, router: IntentRouter):
        """Test 'hello' is detected as greeting."""
        result = router._should_handle_directly("hello")

        assert result is not None
        assert result.handle_directly is True
        assert result.agent_name is None
        assert result.confidence == 1.0
        assert "hello" in result.reasoning.lower()

    def test_greeting_hi_detected(self, router: IntentRouter):
        """Test 'hi' is detected as greeting."""
        result = router._should_handle_directly("hi")

        assert result is not None
        assert result.handle_directly is True

    def test_greeting_hey_detected(self, router: IntentRouter):
        """Test 'hey' is detected as greeting."""
        result = router._should_handle_directly("hey")

        assert result is not None
        assert result.handle_directly is True

    def test_greeting_at_start_of_sentence(self, router: IntentRouter):
        """Test greeting at start of sentence."""
        result = router._should_handle_directly("hello, how are you?")

        assert result is not None
        assert result.handle_directly is True

    def test_thanks_detected(self, router: IntentRouter):
        """Test 'thank you' is detected."""
        result = router._should_handle_directly("thank you")

        assert result is not None
        assert result.handle_directly is True
        assert "thank" in result.reasoning.lower()

    def test_thanks_in_sentence(self, router: IntentRouter):
        """Test thanks in middle of sentence."""
        result = router._should_handle_directly("ok, thanks for the help")

        assert result is not None
        assert result.handle_directly is True

    def test_non_greeting_returns_none(self, router: IntentRouter):
        """Test non-greeting query returns None."""
        result = router._should_handle_directly("check my emails")

        assert result is None

    def test_case_insensitive(self, router: IntentRouter):
        """Test greeting detection is case insensitive."""
        result_lower = router._should_handle_directly("hello")
        result_upper = router._should_handle_directly("HELLO")
        result_mixed = router._should_handle_directly("Hello")

        assert all(r is not None for r in [result_lower, result_upper, result_mixed])
        assert all(r.handle_directly for r in [result_lower, result_upper, result_mixed])


class TestFollowUpDetection:
    """Test suite for _check_follow_up."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the registry before and after each test."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    @pytest.fixture
    def router_with_agent(self):
        """Create router with a registered agent."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail"))
        config = OrchestratorConfig()
        return IntentRouter(registry, config)

    def test_follow_up_detected_with_context(self, router_with_agent: IntentRouter):
        """Test follow-up detection with valid context."""
        context = ConversationContext()
        context.add_turn(
            query="check my emails",
            response="You have 3 unread emails",
            agent="gmail",
        )

        result = router_with_agent._check_follow_up("what about the unread ones?", context)

        assert result is not None
        assert result.agent_name == "gmail"
        assert result.confidence == 0.9
        assert "follow-up" in result.reasoning.lower()

    def test_follow_up_returns_none_when_context_none(
        self, router_with_agent: IntentRouter
    ):
        """Test returns None when context is None."""
        result = router_with_agent._check_follow_up("what about those?", None)

        assert result is None

    def test_follow_up_returns_none_when_disabled(self):
        """Test returns None when follow_up_detection disabled."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail"))
        config = OrchestratorConfig(follow_up_detection=False)
        router = IntentRouter(registry, config)

        context = ConversationContext()
        context.add_turn(
            query="check my emails",
            response="You have 3 unread emails",
            agent="gmail",
        )

        result = router._check_follow_up("what about those?", context)

        assert result is None

    def test_follow_up_returns_none_when_agent_not_in_registry(self):
        """Test returns None when agent no longer in registry."""
        registry = AgentRegistry()
        # Don't register gmail agent
        config = OrchestratorConfig()
        router = IntentRouter(registry, config)

        context = ConversationContext()
        context.add_turn(
            query="check my emails",
            response="You have 3 unread emails",
            agent="gmail",  # Not registered
        )

        result = router._check_follow_up("what about those?", context)

        assert result is None

    def test_follow_up_returns_none_for_new_topic(
        self, router_with_agent: IntentRouter
    ):
        """Test returns None for clearly new topic."""
        context = ConversationContext()
        context.add_turn(
            query="check my emails",
            response="You have 3 unread emails",
            agent="gmail",
        )

        # New topic query without follow-up indicators
        result = router_with_agent._check_follow_up(
            "what is the weather like today?", context
        )

        assert result is None


class TestLLMRouting:
    """Test suite for LLM routing methods."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the registry before and after each test."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    @pytest.fixture
    def router_with_mock_client(self):
        """Create router with mocked Anthropic client."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail", "Email agent"))
        registry.register(MockAgent("calendar", "Calendar agent"))
        config = OrchestratorConfig()
        mock_client = MagicMock()
        return IntentRouter(registry, config, anthropic_client=mock_client)

    def test_parse_llm_response_valid_format(self):
        """Test _parse_llm_response with valid format."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail"))
        config = OrchestratorConfig()
        router = IntentRouter(registry, config)

        response_text = """AGENT: gmail
CONFIDENCE: 0.85
REASONING: Query is about email"""

        result = router._parse_llm_response(response_text)

        assert result.agent_name == "gmail"
        assert result.confidence == pytest.approx(0.85)
        assert result.reasoning == "Query is about email"
        assert result.handle_directly is False

    def test_parse_llm_response_direct(self):
        """Test _parse_llm_response with AGENT: DIRECT."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        router = IntentRouter(registry, config)

        response_text = """AGENT: DIRECT
CONFIDENCE: 1.0
REASONING: This is a greeting"""

        result = router._parse_llm_response(response_text)

        assert result.agent_name is None
        assert result.handle_directly is True

    def test_parse_llm_response_invalid_agent(self):
        """Test _parse_llm_response with unknown agent falls back to direct."""
        registry = AgentRegistry()
        # Don't register any agents
        config = OrchestratorConfig()
        router = IntentRouter(registry, config)

        response_text = """AGENT: unknown_agent
CONFIDENCE: 0.9
REASONING: Some reasoning"""

        result = router._parse_llm_response(response_text)

        assert result.agent_name is None
        assert result.handle_directly is True
        assert "unknown agent" in result.reasoning.lower()

    def test_parse_llm_response_confidence_clamping(self):
        """Test confidence is clamped to 0.0-1.0."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail"))
        config = OrchestratorConfig()
        router = IntentRouter(registry, config)

        # Test above 1.0
        response_high = """AGENT: gmail
CONFIDENCE: 1.5
REASONING: test"""
        result_high = router._parse_llm_response(response_high)
        assert result_high.confidence == 1.0

        # Test below 0.0
        response_low = """AGENT: gmail
CONFIDENCE: -0.5
REASONING: test"""
        result_low = router._parse_llm_response(response_low)
        assert result_low.confidence == 0.0

    def test_parse_llm_response_missing_fields(self):
        """Test _parse_llm_response with missing fields uses defaults."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        router = IntentRouter(registry, config)

        response_text = "Some random text without proper format"

        result = router._parse_llm_response(response_text)

        # Should use defaults
        assert result.confidence == 0.5
        assert result.reasoning == "LLM routing"

    def test_handle_llm_error_uses_code_classification(self):
        """Test _handle_llm_error uses code classification when available."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail"))
        config = OrchestratorConfig()
        router = IntentRouter(registry, config)

        classification = ClassificationResult(
            agent_name="gmail",
            confidence=0.5,
            needs_llm_routing=True,
        )

        result = router._handle_llm_error(classification, "API timeout")

        assert result.agent_name == "gmail"
        assert result.confidence == 0.5
        assert "API timeout" in result.reasoning
        assert result.handle_directly is False

    def test_handle_llm_error_handles_directly_when_no_match(self):
        """Test _handle_llm_error handles directly when no good match."""
        registry = AgentRegistry()
        config = OrchestratorConfig()
        router = IntentRouter(registry, config)

        classification = ClassificationResult(
            agent_name=None,
            confidence=0.0,
            needs_llm_routing=True,
        )

        result = router._handle_llm_error(classification, "API error")

        assert result.agent_name is None
        assert result.handle_directly is True
        assert "API error" in result.reasoning

    @pytest.mark.asyncio
    async def test_llm_route_with_mocked_client(
        self, router_with_mock_client: IntentRouter
    ):
        """Test _llm_route with mocked Anthropic client."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="AGENT: gmail\nCONFIDENCE: 0.85\nREASONING: Email query")
        ]
        router_with_mock_client._client.messages.create.return_value = mock_response

        classification = ClassificationResult(
            agent_name=None,
            confidence=0.3,
            needs_llm_routing=True,
        )

        result = await router_with_mock_client._llm_route(
            "check something in my email", classification, None
        )

        assert result.agent_name == "gmail"
        assert result.confidence == pytest.approx(0.85)
        router_with_mock_client._client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_route_includes_context(
        self, router_with_mock_client: IntentRouter
    ):
        """Test _llm_route includes conversation context in prompt."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="AGENT: gmail\nCONFIDENCE: 0.9\nREASONING: Follow-up")
        ]
        router_with_mock_client._client.messages.create.return_value = mock_response

        context = ConversationContext()
        context.add_turn(
            query="check my email",
            response="You have 3 emails",
            agent="gmail",
        )

        classification = ClassificationResult(
            agent_name=None,
            confidence=0.3,
            needs_llm_routing=True,
        )

        await router_with_mock_client._llm_route("what about now?", classification, context)

        # Verify context was included in the call
        call_args = router_with_mock_client._client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        assert "Recent conversation" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_llm_route_handles_api_exception(
        self, router_with_mock_client: IntentRouter
    ):
        """Test _llm_route handles API exceptions gracefully."""
        router_with_mock_client._client.messages.create.side_effect = Exception(
            "API Error"
        )

        classification = ClassificationResult(
            agent_name="gmail",
            confidence=0.4,
            needs_llm_routing=True,
        )

        result = await router_with_mock_client._llm_route(
            "some query", classification, None
        )

        # Should fall back to code classification
        assert result.agent_name == "gmail"
        assert "API Error" in result.reasoning


class TestRouteMethod:
    """Test suite for main route() method."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the registry before and after each test."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    @pytest.fixture
    def router_with_agents(self):
        """Create router with registered agents and mocked LLM."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail", "Email agent"))
        registry.register(MockAgent("calendar", "Calendar agent"))
        config = OrchestratorConfig()
        mock_client = MagicMock()
        return IntentRouter(registry, config, anthropic_client=mock_client)

    @pytest.mark.asyncio
    async def test_follow_up_takes_priority(self, router_with_agents: IntentRouter):
        """Test that follow-up detection takes priority."""
        context = ConversationContext()
        context.add_turn(
            query="check my emails",
            response="You have 3 unread emails",
            agent="gmail",
        )

        result = await router_with_agents.route("what about the unread ones?", context)

        assert result.agent_name == "gmail"
        assert "follow-up" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_greetings_handled_directly(self, router_with_agents: IntentRouter):
        """Test that greetings are handled directly."""
        result = await router_with_agents.route("hello")

        assert result.handle_directly is True
        assert result.agent_name is None

    @pytest.mark.asyncio
    async def test_high_confidence_code_classification(
        self, router_with_agents: IntentRouter
    ):
        """Test high-confidence code classification returns immediately."""
        result = await router_with_agents.route("check my unread emails")

        assert result.agent_name == "gmail"
        assert result.confidence >= 0.7
        assert "code-based" in result.reasoning.lower()
        # LLM should not be called
        router_with_agents._client.messages.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_low_confidence_triggers_llm(self, router_with_agents: IntentRouter):
        """Test low confidence triggers LLM routing."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="AGENT: gmail\nCONFIDENCE: 0.7\nREASONING: Best match")
        ]
        router_with_agents._client.messages.create.return_value = mock_response

        # Query that's ambiguous
        result = await router_with_agents.route("help me with something")

        # LLM should be called
        router_with_agents._client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_disabled_fallback(self):
        """Test fallback when LLM routing is disabled."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail"))
        config = OrchestratorConfig(llm_routing_enabled=False)
        router = IntentRouter(registry, config)

        # Low confidence query
        result = await router.route("something about email maybe")

        # Should use best-effort code classification
        assert result.agent_name is not None or result.handle_directly is True

    @pytest.mark.asyncio
    async def test_no_match_handles_directly(self):
        """Test no match results in direct handling."""
        registry = AgentRegistry()
        # No agents registered
        config = OrchestratorConfig(llm_routing_enabled=False)
        router = IntentRouter(registry, config)

        result = await router.route("random query with no match")

        assert result.handle_directly is True
        assert result.agent_name is None


class TestIntegration:
    """Integration tests with real agent registry."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the registry before and after each test."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    @pytest.mark.asyncio
    async def test_full_routing_flow_email(self):
        """Test full routing flow for email query."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail", "Email agent"))
        config = OrchestratorConfig()
        router = IntentRouter(registry, config)

        result = await router.route("check my unread emails")

        assert result.agent_name == "gmail"
        assert result.confidence >= 0.7
        assert result.handle_directly is False

    @pytest.mark.asyncio
    async def test_full_routing_flow_greeting(self):
        """Test full routing flow for greeting."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail", "Email agent"))
        config = OrchestratorConfig()
        router = IntentRouter(registry, config)

        result = await router.route("hello there!")

        assert result.handle_directly is True
        assert result.agent_name is None
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_full_routing_flow_follow_up(self):
        """Test full routing flow for follow-up."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail", "Email agent"))
        config = OrchestratorConfig()
        router = IntentRouter(registry, config)

        context = ConversationContext()
        context.add_turn(
            query="check my emails",
            response="You have 5 unread emails",
            agent="gmail",
        )

        result = await router.route("tell me more about them", context)

        assert result.agent_name == "gmail"
        assert "follow-up" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_full_routing_flow_ambiguous_with_mock_llm(self):
        """Test full routing flow for ambiguous query with mocked LLM."""
        registry = AgentRegistry()
        registry.register(MockAgent("gmail", "Email agent"))
        registry.register(MockAgent("calendar", "Calendar agent"))
        config = OrchestratorConfig()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="AGENT: calendar\nCONFIDENCE: 0.7\nREASONING: Meeting-related"
            )
        ]
        mock_client.messages.create.return_value = mock_response

        router = IntentRouter(registry, config, anthropic_client=mock_client)

        result = await router.route("email about meeting schedule")

        # Should have triggered LLM and got calendar
        assert result.agent_name == "calendar"
        mock_client.messages.create.assert_called_once()


class TestModuleExports:
    """Test that router exports are available from orchestrator module."""

    def test_intent_router_importable(self):
        """Test IntentRouter importable from clarvis_agents.orchestrator."""
        from clarvis_agents.orchestrator import IntentRouter

        assert IntentRouter is not None

    def test_routing_decision_importable(self):
        """Test RoutingDecision importable from clarvis_agents.orchestrator."""
        from clarvis_agents.orchestrator import RoutingDecision

        assert RoutingDecision is not None

    def test_all_list_updated(self):
        """Test __all__ contains new exports."""
        from clarvis_agents import orchestrator

        assert "IntentRouter" in orchestrator.__all__
        assert "RoutingDecision" in orchestrator.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
