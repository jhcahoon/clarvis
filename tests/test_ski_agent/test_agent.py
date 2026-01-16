"""Tests for Ski Agent."""

import pytest
from unittest.mock import patch, AsyncMock

from clarvis_agents.ski_agent import SkiAgent, create_ski_agent, SkiAgentConfig
from clarvis_agents.core import (
    AgentCapability,
    AgentRegistry,
    AgentResponse,
    BaseAgent,
)


class TestSkiAgent:
    """Test suite for Ski Agent."""

    def test_agent_initialization(self):
        """Test agent can be created."""
        agent = create_ski_agent()
        assert agent is not None
        assert isinstance(agent, SkiAgent)

    def test_agent_with_custom_config(self):
        """Test agent with custom configuration."""
        config = SkiAgentConfig(max_turns=20)
        agent = SkiAgent(config)
        assert agent.config.max_turns == 20


class TestSkiAgentBaseAgent:
    """Test suite for SkiAgent BaseAgent interface implementation."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the registry before and after each test."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    def test_inherits_from_base_agent(self):
        """Test that SkiAgent inherits from BaseAgent."""
        agent = SkiAgent()
        assert isinstance(agent, BaseAgent)

    def test_name_property(self):
        """Test that name property returns 'ski'."""
        agent = SkiAgent()
        assert agent.name == "ski"

    def test_description_property(self):
        """Test that description property returns expected value."""
        agent = SkiAgent()
        assert agent.description == "Report ski conditions for Mt Hood Meadows"

    def test_capabilities_property(self):
        """Test that capabilities property returns correct structure."""
        agent = SkiAgent()
        capabilities = agent.capabilities

        assert len(capabilities) == 4
        assert all(isinstance(cap, AgentCapability) for cap in capabilities)

        # Check capability names
        cap_names = [cap.name for cap in capabilities]
        assert "snow_conditions" in cap_names
        assert "lift_status" in cap_names
        assert "weather" in cap_names
        assert "full_report" in cap_names

        # Check structure of first capability
        snow_cap = next(cap for cap in capabilities if cap.name == "snow_conditions")
        assert "snow" in snow_cap.description.lower()
        assert len(snow_cap.keywords) > 0
        assert len(snow_cap.examples) > 0

    @pytest.mark.asyncio
    async def test_process_success(self):
        """Test that process method returns AgentResponse on success."""
        agent = SkiAgent()

        # Mock the internal async method to avoid actual API calls
        with patch.object(
            agent, "_get_conditions", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = "Meadows has 72 inches at mid-mountain."

            response = await agent.process("What's the ski report?")

            assert isinstance(response, AgentResponse)
            assert response.success is True
            assert response.agent_name == "ski"
            assert response.content == "Meadows has 72 inches at mid-mountain."
            assert response.error is None
            mock_get.assert_called_once_with("What's the ski report?")

    @pytest.mark.asyncio
    async def test_process_error_handling(self):
        """Test that process method handles errors gracefully."""
        agent = SkiAgent()

        # Mock the internal async method to raise an exception
        with patch.object(
            agent, "_get_conditions", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = RuntimeError("Connection failed")

            response = await agent.process("What's the ski report?")

            assert isinstance(response, AgentResponse)
            assert response.success is False
            assert response.agent_name == "ski"
            assert "Error getting ski conditions" in response.content
            assert response.error == "Connection failed"

    def test_health_check(self):
        """Test that health_check returns True."""
        agent = SkiAgent()
        assert agent.health_check() is True

    def test_can_register_with_registry(self):
        """Test that SkiAgent can be registered with AgentRegistry."""
        agent = SkiAgent()
        registry = AgentRegistry()

        registry.register(agent)

        assert "ski" in registry.list_agents()
        assert registry.get("ski") is agent

    def test_registry_capabilities_include_ski(self):
        """Test that registry reports Ski agent capabilities correctly."""
        agent = SkiAgent()
        registry = AgentRegistry()
        registry.register(agent)

        all_caps = registry.get_all_capabilities()

        assert "ski" in all_caps
        assert len(all_caps["ski"]) == 4

    def test_registry_health_check_includes_ski(self):
        """Test that registry health check includes Ski agent."""
        agent = SkiAgent()
        registry = AgentRegistry()
        registry.register(agent)

        health = registry.health_check_all()

        assert "ski" in health
        assert health["ski"] is True


class TestSkiAgentRateLimiting:
    """Test suite for Ski Agent rate limiting."""

    def test_rate_limiter_initialized(self):
        """Test that rate limiter is initialized."""
        agent = SkiAgent()
        assert agent.rate_limiter is not None

    @pytest.mark.asyncio
    async def test_stream_rate_limit_exceeded(self):
        """Test that stream method respects rate limiting."""
        config = SkiAgentConfig(max_requests_per_minute=1)
        agent = SkiAgent(config)

        # First call should pass through to stream
        with patch.object(agent, "_build_agent_options"):
            with patch("clarvis_agents.ski_agent.agent.query") as mock_query:
                mock_query.return_value = AsyncMock()
                mock_query.return_value.__aiter__.return_value = iter([])

                # First call
                results1 = []
                async for chunk in agent.stream("first query"):
                    results1.append(chunk)

        # Second call should be rate limited
        results2 = []
        async for chunk in agent.stream("second query"):
            results2.append(chunk)

        assert any("Rate limit exceeded" in r for r in results2)


class TestSkiAgentPromptBuilding:
    """Test suite for Ski Agent prompt construction."""

    def test_build_conditions_prompt(self):
        """Test that prompt includes URL and user query."""
        agent = SkiAgent()
        prompt = agent._build_conditions_prompt("What's the snow report?")

        assert agent.config.meadows_url in prompt
        assert "What's the snow report?" in prompt
        assert "fetch" in prompt.lower()


class TestCreateSkiAgent:
    """Test suite for create_ski_agent factory function."""

    def test_factory_creates_agent(self):
        """Test that factory creates a SkiAgent instance."""
        agent = create_ski_agent()
        assert isinstance(agent, SkiAgent)

    def test_factory_creates_with_default_config(self):
        """Test that factory uses default configuration."""
        agent = create_ski_agent()
        assert agent.config.model == "claude-3-5-haiku-20241022"
        assert agent.config.max_turns == 10
        assert agent.config.meadows_url == "https://cloudserv.skihood.com/"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
