"""Tests for BaseAgent, AgentResponse, and AgentCapability (Issue #18)."""

import pytest
from typing import Optional

from clarvis_agents.core import (
    AgentCapability,
    AgentResponse,
    BaseAgent,
    ConversationContext,
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


class TestAgentResponseEdgeCases:
    """Additional edge case tests for AgentResponse."""

    def test_response_with_empty_content(self):
        """Test AgentResponse with empty content string."""
        response = AgentResponse(
            content="",
            success=True,
            agent_name="test",
        )
        assert response.content == ""
        assert response.success is True

    def test_response_with_large_metadata(self):
        """Test AgentResponse with large metadata dictionary."""
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(100)}
        response = AgentResponse(
            content="Test",
            success=True,
            agent_name="test",
            metadata=large_metadata,
        )
        assert len(response.metadata) == 100

    def test_response_with_nested_metadata(self):
        """Test AgentResponse with nested metadata structures."""
        nested_metadata = {
            "emails": [
                {"id": 1, "subject": "Test"},
                {"id": 2, "subject": "Hello"},
            ],
            "summary": {"total": 2, "unread": 1},
        }
        response = AgentResponse(
            content="Found emails",
            success=True,
            agent_name="gmail",
            metadata=nested_metadata,
        )
        assert response.metadata["emails"][0]["subject"] == "Test"
        assert response.metadata["summary"]["total"] == 2


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


class TestBaseAgentAsync:
    """Test async behavior of BaseAgent implementations."""

    @pytest.mark.asyncio
    async def test_concrete_agent_process_is_async(self):
        """Test that process method works asynchronously."""

        class AsyncTestAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "async_test"

            @property
            def description(self) -> str:
                return "Async test agent"

            @property
            def capabilities(self) -> list[AgentCapability]:
                return []

            async def process(
                self, query: str, context: Optional[ConversationContext] = None
            ) -> AgentResponse:
                return AgentResponse(
                    content=f"Async response to: {query}",
                    success=True,
                    agent_name=self.name,
                )

            def health_check(self) -> bool:
                return True

        agent = AsyncTestAgent()
        response = await agent.process("test query")

        assert response.success is True
        assert response.content == "Async response to: test query"
        assert response.agent_name == "async_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
