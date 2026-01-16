"""Tests for Notes Agent."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, AsyncMock

from clarvis_agents.notes_agent import NotesAgent, create_notes_agent, NotesAgentConfig
from clarvis_agents.core import (
    AgentCapability,
    AgentRegistry,
    AgentResponse,
    BaseAgent,
)


class TestNotesAgent:
    """Test suite for Notes Agent."""

    @pytest.fixture
    def temp_config(self):
        """Create config with temporary directories."""
        with TemporaryDirectory() as tmpdir:
            config = NotesAgentConfig(
                notes_dir=Path(tmpdir) / "notes",
                log_dir=Path(tmpdir) / "logs",
            )
            yield config

    def test_agent_initialization(self, temp_config: NotesAgentConfig):
        """Test agent can be created."""
        agent = NotesAgent(temp_config)
        assert agent is not None
        assert isinstance(agent, NotesAgent)

    def test_agent_with_custom_config(self, temp_config: NotesAgentConfig):
        """Test agent with custom configuration."""
        temp_config.max_turns = 20
        agent = NotesAgent(temp_config)
        assert agent.config.max_turns == 20


class TestNotesAgentBaseAgent:
    """Test suite for NotesAgent BaseAgent interface implementation."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the registry before and after each test."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    @pytest.fixture
    def temp_config(self):
        """Create config with temporary directories."""
        with TemporaryDirectory() as tmpdir:
            config = NotesAgentConfig(
                notes_dir=Path(tmpdir) / "notes",
                log_dir=Path(tmpdir) / "logs",
            )
            yield config

    def test_inherits_from_base_agent(self, temp_config: NotesAgentConfig):
        """Test that NotesAgent inherits from BaseAgent."""
        agent = NotesAgent(temp_config)
        assert isinstance(agent, BaseAgent)

    def test_name_property(self, temp_config: NotesAgentConfig):
        """Test that name property returns 'notes'."""
        agent = NotesAgent(temp_config)
        assert agent.name == "notes"

    def test_description_property(self, temp_config: NotesAgentConfig):
        """Test that description property returns expected value."""
        agent = NotesAgent(temp_config)
        assert "notes" in agent.description.lower() or "list" in agent.description.lower()

    def test_capabilities_property(self, temp_config: NotesAgentConfig):
        """Test that capabilities property returns correct structure."""
        agent = NotesAgent(temp_config)
        capabilities = agent.capabilities

        assert len(capabilities) == 4
        assert all(isinstance(cap, AgentCapability) for cap in capabilities)

        # Check capability names
        cap_names = [cap.name for cap in capabilities]
        assert "manage_lists" in cap_names
        assert "reminders" in cap_names
        assert "notes" in cap_names
        assert "list_management" in cap_names

        # Check structure of first capability
        list_cap = next(cap for cap in capabilities if cap.name == "manage_lists")
        assert len(list_cap.keywords) > 0
        assert len(list_cap.examples) > 0

    @pytest.mark.asyncio
    async def test_process_success(self, temp_config: NotesAgentConfig):
        """Test that process method returns AgentResponse on success."""
        agent = NotesAgent(temp_config)

        # Mock the internal async method to avoid actual API calls
        with patch.object(
            agent, "_handle_query", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.return_value = "Added milk to your grocery list."

            response = await agent.process("Add milk to grocery list")

            assert isinstance(response, AgentResponse)
            assert response.success is True
            assert response.agent_name == "notes"
            assert response.content == "Added milk to your grocery list."
            assert response.error is None
            mock_handle.assert_called_once_with("Add milk to grocery list")

    @pytest.mark.asyncio
    async def test_process_error_handling(self, temp_config: NotesAgentConfig):
        """Test that process method handles errors gracefully."""
        agent = NotesAgent(temp_config)

        # Mock the internal async method to raise an exception
        with patch.object(
            agent, "_handle_query", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.side_effect = RuntimeError("Something went wrong")

            response = await agent.process("Add milk to grocery list")

            assert isinstance(response, AgentResponse)
            assert response.success is False
            assert response.agent_name == "notes"
            assert "Error" in response.content
            assert response.error == "Something went wrong"

    def test_health_check(self, temp_config: NotesAgentConfig):
        """Test that health_check returns True when storage accessible."""
        agent = NotesAgent(temp_config)
        assert agent.health_check() is True

    def test_can_register_with_registry(self, temp_config: NotesAgentConfig):
        """Test that NotesAgent can be registered with AgentRegistry."""
        agent = NotesAgent(temp_config)
        registry = AgentRegistry()

        registry.register(agent)

        assert "notes" in registry.list_agents()
        assert registry.get("notes") is agent

    def test_registry_capabilities_include_notes(self, temp_config: NotesAgentConfig):
        """Test that registry reports Notes agent capabilities correctly."""
        agent = NotesAgent(temp_config)
        registry = AgentRegistry()
        registry.register(agent)

        all_caps = registry.get_all_capabilities()

        assert "notes" in all_caps
        assert len(all_caps["notes"]) == 4

    def test_registry_health_check_includes_notes(self, temp_config: NotesAgentConfig):
        """Test that registry health check includes Notes agent."""
        agent = NotesAgent(temp_config)
        registry = AgentRegistry()
        registry.register(agent)

        health = registry.health_check_all()

        assert "notes" in health
        assert health["notes"] is True


class TestNotesAgentRateLimiting:
    """Test suite for Notes Agent rate limiting."""

    @pytest.fixture
    def temp_config(self):
        """Create config with temporary directories."""
        with TemporaryDirectory() as tmpdir:
            config = NotesAgentConfig(
                notes_dir=Path(tmpdir) / "notes",
                log_dir=Path(tmpdir) / "logs",
            )
            yield config

    def test_rate_limiter_initialized(self, temp_config: NotesAgentConfig):
        """Test that rate limiter is initialized."""
        agent = NotesAgent(temp_config)
        assert agent.rate_limiter is not None

    @pytest.mark.asyncio
    async def test_stream_rate_limit_exceeded(self, temp_config: NotesAgentConfig):
        """Test that stream method respects rate limiting."""
        temp_config.max_requests_per_minute = 1
        agent = NotesAgent(temp_config)

        # First call should pass through to stream
        with patch.object(agent, "_build_agent_options"):
            with patch("clarvis_agents.notes_agent.agent.query") as mock_query:
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


class TestCreateNotesAgent:
    """Test suite for create_notes_agent factory function."""

    def test_factory_creates_agent(self):
        """Test that factory creates a NotesAgent instance."""
        with TemporaryDirectory() as tmpdir:
            config = NotesAgentConfig(
                notes_dir=Path(tmpdir) / "notes",
                log_dir=Path(tmpdir) / "logs",
            )
            agent = create_notes_agent(config)
            assert isinstance(agent, NotesAgent)

    def test_factory_creates_with_default_config(self):
        """Test that factory uses default configuration."""
        with TemporaryDirectory() as tmpdir:
            config = NotesAgentConfig(
                notes_dir=Path(tmpdir) / "notes",
                log_dir=Path(tmpdir) / "logs",
            )
            agent = create_notes_agent(config)
            assert agent.config.model == "claude-3-5-haiku-20241022"
            assert agent.config.max_turns == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
