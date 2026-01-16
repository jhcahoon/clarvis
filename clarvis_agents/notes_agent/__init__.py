"""Notes Agent - Manage notes, lists, reminders, and quick information."""

from .agent import NotesAgent, create_notes_agent
from .config import NotesAgentConfig, RateLimiter
from .storage import Note, NotesStorage

__all__ = [
    "NotesAgent",
    "create_notes_agent",
    "NotesAgentConfig",
    "RateLimiter",
    "Note",
    "NotesStorage",
]

__version__ = "1.0.0"
