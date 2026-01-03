"""Configuration for Gmail Agent."""

from dataclasses import dataclass
from typing import Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque


class RateLimiter:
    """Rate limiter using sliding window algorithm."""

    def __init__(self, max_calls: int, time_window: timedelta):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in the time window
            time_window: Time window for rate limiting
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()

    def check_rate_limit(self) -> bool:
        """
        Check if we're within rate limit.

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
class GmailAgentConfig:
    """Configuration for Gmail Agent."""

    # Model configuration
    # Using Claude Agent SDK (native Anthropic integration)
    # claude-3-5-haiku is fast and cost-effective for email tasks
    # Alternative: claude-3-5-sonnet-20241022 for higher quality
    model: str = "claude-3-5-haiku-20241022"
    max_turns: int = 30

    # Paths
    gmail_mcp_path: Path = Path.home() / ".gmail-mcp"
    log_dir: Path = Path(__file__).parent.parent.parent / "logs" / "gmail_agent"

    # Permission scopes
    read_only: bool = True

    # Rate limiting
    max_searches_per_minute: int = 10
    max_emails_per_search: int = 50

    def __post_init__(self) -> None:
        """Ensure paths are Path objects."""
        if not isinstance(self.gmail_mcp_path, Path):
            self.gmail_mcp_path = Path(self.gmail_mcp_path)
        if not isinstance(self.log_dir, Path):
            self.log_dir = Path(self.log_dir)

    def get_mcp_config(self) -> Dict[str, Any]:
        """
        Returns MCP server configuration dictionary.

        Returns:
            Dictionary with MCP server configuration
        """
        return {
            "gmail": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
                "env": {
                    "GMAIL_OAUTH_PATH": str(self.gmail_mcp_path / "gcp-oauth.keys.json"),
                    "GMAIL_CREDENTIALS_PATH": str(self.gmail_mcp_path / "credentials.json"),
                }
            }
        }

    def get_blocked_tools(self) -> list[str]:
        """
        Returns list of tools to block when in read-only mode.

        Claude Agent SDK uses mcp__<server>__<tool> naming convention.

        Returns:
            List of tool names to block (with MCP prefixes)
        """
        if self.read_only:
            return [
                "mcp__gmail__gmail_send_email",
                "mcp__gmail__gmail_delete_email",
                "mcp__gmail__gmail_modify_labels",
                "mcp__gmail__gmail_trash_email",
                "mcp__gmail__gmail_untrash_email",
            ]
        return []
