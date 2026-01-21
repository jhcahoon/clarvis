"""Configuration for Ski Agent."""

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


class RateLimiter:
    """Thread-safe rate limiter using sliding window algorithm."""

    def __init__(self, max_calls: int, time_window: timedelta) -> None:
        """Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in the time window
            time_window: Time window for rate limiting
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: deque[datetime] = deque()
        self._lock = threading.Lock()

    def check_rate_limit(self) -> bool:
        """Check if we're within rate limit (thread-safe).

        Returns:
            True if within rate limit, False otherwise
        """
        now = datetime.now()

        with self._lock:
            # Remove old calls outside the time window
            while self.calls and self.calls[0] < now - self.time_window:
                self.calls.popleft()

            # Check if we've exceeded the limit
            if len(self.calls) >= self.max_calls:
                return False

            # Record this call
            self.calls.append(now)
            return True


@dataclass
class CachedConditions:
    """Cached ski conditions data."""

    data: str
    timestamp: datetime

    def is_expired(self, ttl_minutes: int) -> bool:
        """Check if cache has expired.

        Args:
            ttl_minutes: Time-to-live in minutes

        Returns:
            True if cache has expired
        """
        return datetime.now() - self.timestamp > timedelta(minutes=ttl_minutes)


@dataclass
class SkiAgentConfig:
    """Configuration for Ski Agent."""

    # Model configuration
    model: str = "claude-3-5-haiku-20241022"
    max_turns: int = 10

    # Data source
    meadows_url: str = "https://cloudserv.skihood.com/"

    # Caching
    cache_ttl_minutes: int = 15  # Cache conditions to avoid excessive requests

    # Rate limiting
    max_requests_per_minute: int = 5

    # Logging
    log_dir: Path = Path(__file__).parent.parent.parent / "logs" / "ski_agent"

    def __post_init__(self) -> None:
        """Ensure paths are Path objects."""
        if not isinstance(self.log_dir, Path):
            self.log_dir = Path(self.log_dir)
