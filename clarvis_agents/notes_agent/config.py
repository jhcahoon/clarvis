"""Configuration for Notes Agent."""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


class RateLimiter:
    """Rate limiter using sliding window algorithm."""

    def __init__(self, max_calls: int, time_window: timedelta):
        """Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in the time window
            time_window: Time window for rate limiting
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: deque[datetime] = deque()

    def check_rate_limit(self) -> bool:
        """Check if we're within rate limit.

        Returns:
            True if within rate limit, False otherwise
        """
        now = datetime.now()

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
class NotesAgentConfig:
    """Configuration for Notes Agent."""

    # Model configuration
    model: str = "claude-3-5-haiku-20241022"
    max_turns: int = 10

    # Storage paths
    notes_dir: Path = Path.home() / ".clarvis" / "notes"
    log_dir: Path = Path(__file__).parent.parent.parent / "logs" / "notes_agent"

    # Rate limiting
    max_requests_per_minute: int = 30  # Higher limit for local operations

    def __post_init__(self) -> None:
        """Ensure paths are Path objects."""
        if not isinstance(self.notes_dir, Path):
            self.notes_dir = Path(self.notes_dir)
        if not isinstance(self.log_dir, Path):
            self.log_dir = Path(self.log_dir)
