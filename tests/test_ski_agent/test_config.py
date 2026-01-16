"""Tests for Ski Agent configuration."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from clarvis_agents.ski_agent.config import (
    CachedConditions,
    RateLimiter,
    SkiAgentConfig,
)


class TestSkiAgentConfig:
    """Test suite for SkiAgentConfig."""

    def test_config_defaults(self):
        """Test configuration defaults."""
        config = SkiAgentConfig()
        assert config.model == "claude-3-5-haiku-20241022"
        assert config.max_turns == 10
        assert config.meadows_url == "https://cloudserv.skihood.com/"
        assert config.cache_ttl_minutes == 15
        assert config.max_requests_per_minute == 5

    def test_config_custom_values(self):
        """Test configuration with custom values."""
        config = SkiAgentConfig(
            model="claude-sonnet-4-20250514",
            max_turns=20,
            cache_ttl_minutes=30,
            max_requests_per_minute=10,
        )
        assert config.model == "claude-sonnet-4-20250514"
        assert config.max_turns == 20
        assert config.cache_ttl_minutes == 30
        assert config.max_requests_per_minute == 10

    def test_config_mcp_config(self):
        """Test MCP configuration generation."""
        config = SkiAgentConfig()
        mcp_config = config.get_mcp_config()

        assert "fetch" in mcp_config
        assert mcp_config["fetch"]["type"] == "stdio"
        assert mcp_config["fetch"]["command"] == "uvx"
        assert "mcp-server-fetch" in mcp_config["fetch"]["args"]

    def test_config_log_dir_is_path(self):
        """Test that log_dir is a Path object."""
        config = SkiAgentConfig()
        assert isinstance(config.log_dir, Path)

    def test_config_log_dir_custom(self):
        """Test custom log directory."""
        custom_path = Path("/tmp/ski_logs")
        config = SkiAgentConfig(log_dir=custom_path)
        assert config.log_dir == custom_path


class TestCachedConditions:
    """Test suite for CachedConditions."""

    def test_cache_creation(self):
        """Test CachedConditions creation."""
        cache = CachedConditions(
            data="test data",
            timestamp=datetime.now(),
        )
        assert cache.data == "test data"
        assert cache.timestamp is not None

    def test_cache_not_expired(self):
        """Test cache is not expired when within TTL."""
        cache = CachedConditions(
            data="test data",
            timestamp=datetime.now(),
        )
        # Check with 15 minute TTL
        assert cache.is_expired(ttl_minutes=15) is False

    def test_cache_expired(self):
        """Test cache is expired when past TTL."""
        old_timestamp = datetime.now() - timedelta(minutes=20)
        cache = CachedConditions(
            data="test data",
            timestamp=old_timestamp,
        )
        # Check with 15 minute TTL
        assert cache.is_expired(ttl_minutes=15) is True

    def test_cache_exactly_at_expiry(self):
        """Test cache at exact TTL boundary."""
        # Create cache exactly at the boundary
        boundary_timestamp = datetime.now() - timedelta(minutes=15, seconds=1)
        cache = CachedConditions(
            data="test data",
            timestamp=boundary_timestamp,
        )
        assert cache.is_expired(ttl_minutes=15) is True


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
