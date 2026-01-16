"""Integration tests for Ski Agent (requires network access)."""

import pytest

from clarvis_agents.ski_agent import SkiAgent, create_ski_agent


@pytest.mark.integration
@pytest.mark.skip(reason="Integration test - requires network and MCP server")
class TestSkiAgentIntegration:
    """Integration tests for Ski Agent."""

    @pytest.mark.asyncio
    async def test_fetch_conditions(self):
        """Test fetching real ski conditions (integration test)."""
        agent = create_ski_agent()
        response = await agent.process("What's the ski report at Meadows?")

        assert response.success is True
        assert len(response.content) > 0
        # Response should mention something ski-related
        assert any(
            word in response.content.lower()
            for word in ["snow", "inch", "lift", "conditions", "meadows"]
        )

    @pytest.mark.asyncio
    async def test_stream_conditions(self):
        """Test streaming ski conditions (integration test)."""
        agent = create_ski_agent()
        chunks = []

        async for chunk in agent.stream("How much snow at Meadows?"):
            chunks.append(chunk)

        full_response = "".join(chunks)
        assert len(full_response) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
