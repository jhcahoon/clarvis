"""Conversation context management for Clarvis multi-agent architecture."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""

    query: str
    response: str
    agent_used: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationContext:
    """Tracks conversation state across multiple turns."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    turns: list[ConversationTurn] = field(default_factory=list)
    last_agent: Optional[str] = None

    def add_turn(self, query: str, response: str, agent: str) -> None:
        """Add a new turn to the conversation.

        Args:
            query: The user's query.
            response: The agent's response.
            agent: The name of the agent that handled the query.
        """
        turn = ConversationTurn(query=query, response=response, agent_used=agent)
        self.turns.append(turn)
        self.last_agent = agent

    def get_recent_context(self, n: int = 3) -> str:
        """Get formatted string of recent conversation turns.

        Args:
            n: Maximum number of recent turns to include.

        Returns:
            Formatted string with recent conversation history.
        """
        recent = self.turns[-n:] if len(self.turns) > n else self.turns
        lines = []
        for turn in recent:
            lines.append(f"User: {turn.query}")
            lines.append(f"Agent ({turn.agent_used}): {turn.response}")
        return "\n".join(lines)

    def should_continue_with_agent(self, query: str) -> Optional[str]:
        """Detect if this query is a follow-up that should go to the last agent.

        Args:
            query: The user's current query.

        Returns:
            The name of the last agent if this appears to be a follow-up query,
            None otherwise.
        """
        if not self.last_agent or not self.turns:
            return None

        # Follow-up indicators
        follow_up_phrases = [
            "what about",
            "and also",
            "also",
            "more about",
            "tell me more",
            "can you",
            "what else",
            "anything else",
            "the same",
            "that one",
            "those",
            "them",
            "it",
        ]

        query_lower = query.lower().strip()

        # Check for follow-up indicators
        for phrase in follow_up_phrases:
            if query_lower.startswith(phrase):
                return self.last_agent

        # Check for pronouns that likely refer to previous context
        if len(query_lower.split()) <= 5:  # Short queries more likely follow-ups
            pronouns = ["it", "they", "them", "that", "those", "this"]
            # Strip punctuation from words for comparison
            words = [word.strip("?!.,;:'\"") for word in query_lower.split()]
            if any(word in pronouns for word in words):
                return self.last_agent

        return None
