"""Gmail Agent - Natural language Gmail access using Claude Agent SDK."""

from .agent import GmailAgent, create_gmail_agent
from .config import GmailAgentConfig, RateLimiter

__all__ = [
    "GmailAgent",
    "create_gmail_agent",
    "GmailAgentConfig",
    "RateLimiter",
]

__version__ = "1.0.0"
