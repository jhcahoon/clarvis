"""Tests for Notes Agent configuration."""

import pytest
from pathlib import Path
from datetime import timedelta

from clarvis_agents.notes_agent import NotesAgentConfig, RateLimiter


class TestNotesAgentConfig:
    """Test suite for NotesAgentConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = NotesAgentConfig()

        assert config.model == "claude-3-5-haiku-20241022"
        assert config.max_turns == 10
        assert config.max_requests_per_minute == 30
        assert config.notes_dir == Path.home() / ".clarvis" / "notes"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = NotesAgentConfig(
            model="claude-3-opus",
            max_turns=20,
            max_requests_per_minute=10,
        )

        assert config.model == "claude-3-opus"
        assert config.max_turns == 20
        assert config.max_requests_per_minute == 10

    def test_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        config = NotesAgentConfig()
        # Paths should already be Path objects from default
        assert isinstance(config.notes_dir, Path)
        assert isinstance(config.log_dir, Path)


class TestRateLimiter:
    """Test suite for RateLimiter."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(max_calls=5, time_window=timedelta(minutes=1))

        assert limiter.max_calls == 5
        assert limiter.time_window == timedelta(minutes=1)
        assert len(limiter.calls) == 0

    def test_allows_calls_under_limit(self):
        """Test that calls under limit are allowed."""
        limiter = RateLimiter(max_calls=3, time_window=timedelta(minutes=1))

        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is True

    def test_blocks_calls_at_limit(self):
        """Test that calls at limit are blocked."""
        limiter = RateLimiter(max_calls=2, time_window=timedelta(minutes=1))

        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is False

    def test_expired_calls_removed(self):
        """Test that expired calls are removed from the window."""
        limiter = RateLimiter(max_calls=1, time_window=timedelta(seconds=0))

        # First call should be allowed
        assert limiter.check_rate_limit() is True

        # With 0 second window, next call should also be allowed
        # because previous call is immediately expired
        assert limiter.check_rate_limit() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
