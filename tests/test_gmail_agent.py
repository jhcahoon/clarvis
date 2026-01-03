"""Tests for Gmail Agent."""

import pytest
from pathlib import Path
from datetime import timedelta

from clarvis_agents.gmail_agent import create_gmail_agent, GmailAgent
from clarvis_agents.gmail_agent.config import GmailAgentConfig, RateLimiter
from clarvis_agents.gmail_agent.tools import (
    check_inbox,
    summarize_email_thread,
    search_emails_by_date,
    format_email_date,
)


class TestGmailAgentConfig:
    """Test suite for GmailAgentConfig."""

    def test_config_defaults(self):
        """Test configuration defaults."""
        config = GmailAgentConfig()
        assert config.model == "claude-3-5-haiku-20241022"  # Claude Agent SDK with Haiku 3.5
        assert config.read_only is True
        assert config.max_turns == 30
        assert config.max_searches_per_minute == 10
        assert config.max_emails_per_search == 50

    def test_config_mcp_config(self):
        """Test MCP configuration generation."""
        config = GmailAgentConfig()
        mcp_config = config.get_mcp_config()

        assert "gmail" in mcp_config
        assert mcp_config["gmail"]["command"] == "npx"
        assert "-y" in mcp_config["gmail"]["args"]
        assert "@gongrzhe/server-gmail-autoauth-mcp" in mcp_config["gmail"]["args"]

    def test_config_blocked_tools_read_only(self):
        """Test blocked tools in read-only mode."""
        config = GmailAgentConfig(read_only=True)
        blocked = config.get_blocked_tools()

        # Claude Agent SDK uses mcp__<server>__<tool> naming
        assert "mcp__gmail__gmail_send_email" in blocked
        assert "mcp__gmail__gmail_delete_email" in blocked
        assert "mcp__gmail__gmail_modify_labels" in blocked

    def test_config_blocked_tools_write_mode(self):
        """Test blocked tools when read-only is False."""
        config = GmailAgentConfig(read_only=False)
        blocked = config.get_blocked_tools()

        assert len(blocked) == 0

    def test_config_paths_are_path_objects(self):
        """Test that paths are converted to Path objects."""
        config = GmailAgentConfig()
        assert isinstance(config.gmail_mcp_path, Path)
        assert isinstance(config.log_dir, Path)


class TestRateLimiter:
    """Test suite for RateLimiter."""

    def test_rate_limiter_allows_within_limit(self):
        """Test that rate limiter allows calls within limit."""
        limiter = RateLimiter(max_calls=3, time_window=timedelta(seconds=1))

        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is True

    def test_rate_limiter_blocks_over_limit(self):
        """Test that rate limiter blocks calls over limit."""
        limiter = RateLimiter(max_calls=2, time_window=timedelta(seconds=10))

        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is False  # Over limit

    def test_rate_limiter_resets_after_window(self):
        """Test that rate limiter resets after time window."""
        import time

        limiter = RateLimiter(max_calls=1, time_window=timedelta(milliseconds=100))

        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is False  # Over limit

        time.sleep(0.15)  # Wait for window to pass

        assert limiter.check_rate_limit() is True  # Should allow again


class TestGmailAgentTools:
    """Test suite for Gmail Agent tools.

    NOTE: SDK MCP tools are not currently used in the agent due to
    incompatibility with Claude Code CLI subprocess mode. These tests
    are skipped until the SDK supports in-process MCP servers.
    """

    @pytest.mark.skip(reason="SDK MCP tools not compatible with CLI subprocess mode")
    def test_check_inbox_unread_only(self):
        """Test check_inbox tool with unread_only=True."""
        result = check_inbox(max_results=10, unread_only=True)

        assert "is:unread in:inbox" in result
        assert "10" in result
        assert "unread" in result.lower()

    @pytest.mark.skip(reason="SDK MCP tools not compatible with CLI subprocess mode")
    def test_check_inbox_all_emails(self):
        """Test check_inbox tool with unread_only=False."""
        result = check_inbox(max_results=20, unread_only=False)

        assert "in:inbox" in result
        assert "20" in result
        assert "all" in result.lower()

    @pytest.mark.skip(reason="SDK MCP tools not compatible with CLI subprocess mode")
    def test_summarize_email_thread(self):
        """Test summarize_email_thread tool."""
        result = summarize_email_thread(thread_id="12345")

        assert "12345" in result
        assert "gmail_get_thread" in result
        assert "summarize" in result.lower()

    @pytest.mark.skip(reason="SDK MCP tools not compatible with CLI subprocess mode")
    def test_search_emails_by_date_sender(self):
        """Test search_emails_by_date with sender filter."""
        result = search_emails_by_date(sender="john@example.com")

        assert "from:john@example.com" in result

    @pytest.mark.skip(reason="SDK MCP tools not compatible with CLI subprocess mode")
    def test_search_emails_by_date_subject(self):
        """Test search_emails_by_date with subject filter."""
        result = search_emails_by_date(subject_keywords="budget")

        assert "subject:budget" in result

    @pytest.mark.skip(reason="SDK MCP tools not compatible with CLI subprocess mode")
    def test_search_emails_by_date_dates(self):
        """Test search_emails_by_date with date filters."""
        result = search_emails_by_date(
            after_date="2025/01/01",
            before_date="2025/12/31"
        )

        assert "after:2025/01/01" in result
        assert "before:2025/12/31" in result

    @pytest.mark.skip(reason="SDK MCP tools not compatible with CLI subprocess mode")
    def test_search_emails_by_date_days_back(self):
        """Test search_emails_by_date with days_back filter."""
        result = search_emails_by_date(days_back=7)

        assert "after:" in result

    @pytest.mark.skip(reason="SDK MCP tools not compatible with CLI subprocess mode")
    def test_format_email_date_today(self):
        """Test format_email_date with 'today'."""
        result = format_email_date("today")
        from datetime import datetime

        expected = datetime.now().strftime("%Y/%m/%d")
        assert expected in result

    @pytest.mark.skip(reason="SDK MCP tools not compatible with CLI subprocess mode")
    def test_format_email_date_yesterday(self):
        """Test format_email_date with 'yesterday'."""
        result = format_email_date("yesterday")
        from datetime import datetime, timedelta

        expected = (datetime.now() - timedelta(days=1)).strftime("%Y/%m/%d")
        assert expected in result

    @pytest.mark.skip(reason="SDK MCP tools not compatible with CLI subprocess mode")
    def test_format_email_date_last_week(self):
        """Test format_email_date with 'last week'."""
        result = format_email_date("last week")
        from datetime import datetime, timedelta

        expected = (datetime.now() - timedelta(days=7)).strftime("%Y/%m/%d")
        assert expected in result

    @pytest.mark.skip(reason="SDK MCP tools not compatible with CLI subprocess mode")
    def test_format_email_date_days_ago(self):
        """Test format_email_date with 'X days ago'."""
        result = format_email_date("3 days ago")
        from datetime import datetime, timedelta

        expected = (datetime.now() - timedelta(days=3)).strftime("%Y/%m/%d")
        assert expected in result

    @pytest.mark.skip(reason="SDK MCP tools not compatible with CLI subprocess mode")
    def test_format_email_date_invalid(self):
        """Test format_email_date with invalid input."""
        result = format_email_date("invalid date")

        assert "Could not parse" in result


class TestGmailAgent:
    """Test suite for Gmail Agent."""

    def test_agent_initialization(self):
        """Test agent can be created."""
        agent = create_gmail_agent(read_only=True)
        assert agent is not None
        assert isinstance(agent, GmailAgent)

    def test_agent_config(self):
        """Test agent configuration."""
        config = GmailAgentConfig(read_only=True, max_turns=20)
        agent = GmailAgent(config)

        assert agent.config.read_only is True
        assert agent.config.max_turns == 20

    def test_agent_factory_read_only(self):
        """Test factory creates read-only agent."""
        agent = create_gmail_agent(read_only=True)
        assert agent.config.read_only is True

    def test_agent_factory_write_mode(self):
        """Test factory creates write-enabled agent."""
        agent = create_gmail_agent(read_only=False)
        assert agent.config.read_only is False

    @pytest.mark.integration
    def test_agent_check_emails_rate_limit(self):
        """Test that rate limiting works (integration test)."""
        config = GmailAgentConfig(max_searches_per_minute=2)
        agent = GmailAgent(config)

        # First two should work (or fail with MCP error, not rate limit)
        result1 = agent.check_emails("test query 1")
        result2 = agent.check_emails("test query 2")

        # Third should be rate limited
        result3 = agent.check_emails("test query 3")

        assert "Rate limit exceeded" in result3

    @pytest.mark.skip(reason="Async test requires Gmail credentials and pytest-asyncio")
    @pytest.mark.integration
    @pytest.mark.skipif(
        not Path.home().joinpath(".gmail-mcp/credentials.json").exists(),
        reason="Gmail credentials not configured"
    )
    async def test_agent_mcp_connection(self):
        """Test MCP server connectivity (requires setup)."""
        agent = create_gmail_agent()

        # This will try to connect to MCP server
        # Will fail if credentials not set up, but that's expected
        try:
            await agent._initialize_agent()
            assert agent._initialized is True
            await agent.cleanup()
        except Exception as e:
            pytest.skip(f"MCP server not configured: {e}")


# Fixtures for integration tests
@pytest.fixture
def gmail_agent():
    """Fixture that provides a Gmail agent for testing."""
    agent = create_gmail_agent()
    yield agent
    # Cleanup is handled by agent's __del__ method


@pytest.fixture
def gmail_credentials_path():
    """Fixture that provides path to Gmail credentials."""
    return Path.home() / ".gmail-mcp" / "credentials.json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
