"""Tests for ConversationContext and ConversationTurn (Issue #18)."""

import pytest
from datetime import datetime

from clarvis_agents.core import (
    ConversationContext,
    ConversationTurn,
)


class TestConversationTurn:
    """Test suite for ConversationTurn dataclass."""

    def test_turn_with_required_fields(self):
        """Test ConversationTurn with required fields."""
        turn = ConversationTurn(
            query="What's the weather?",
            response="It's sunny today.",
            agent_used="weather",
        )
        assert turn.query == "What's the weather?"
        assert turn.response == "It's sunny today."
        assert turn.agent_used == "weather"

    def test_turn_timestamp_defaults_to_now(self):
        """Test that timestamp defaults to current time."""
        before = datetime.now()
        turn = ConversationTurn(
            query="test",
            response="response",
            agent_used="agent",
        )
        after = datetime.now()

        assert before <= turn.timestamp <= after

    def test_turn_with_explicit_timestamp(self):
        """Test ConversationTurn with explicit timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        turn = ConversationTurn(
            query="test",
            response="response",
            agent_used="agent",
            timestamp=custom_time,
        )
        assert turn.timestamp == custom_time


class TestConversationContext:
    """Test suite for ConversationContext dataclass."""

    def test_context_generates_unique_session_id(self):
        """Test that each context gets a unique session_id."""
        context1 = ConversationContext()
        context2 = ConversationContext()
        assert context1.session_id != context2.session_id

    def test_context_session_id_is_uuid_format(self):
        """Test that session_id is a valid UUID string."""
        context = ConversationContext()
        # UUID format: 8-4-4-4-12 characters
        parts = context.session_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_context_defaults_to_empty_turns(self):
        """Test that turns defaults to empty list."""
        context = ConversationContext()
        assert context.turns == []

    def test_context_defaults_last_agent_to_none(self):
        """Test that last_agent defaults to None."""
        context = ConversationContext()
        assert context.last_agent is None

    def test_add_turn_appends_to_turns(self):
        """Test that add_turn appends a new turn."""
        context = ConversationContext()
        context.add_turn("query1", "response1", "agent1")

        assert len(context.turns) == 1
        assert context.turns[0].query == "query1"
        assert context.turns[0].response == "response1"
        assert context.turns[0].agent_used == "agent1"

    def test_add_turn_updates_last_agent(self):
        """Test that add_turn updates last_agent."""
        context = ConversationContext()
        context.add_turn("query1", "response1", "agent1")
        assert context.last_agent == "agent1"

        context.add_turn("query2", "response2", "agent2")
        assert context.last_agent == "agent2"

    def test_get_recent_context_returns_formatted_string(self):
        """Test get_recent_context returns formatted conversation."""
        context = ConversationContext()
        context.add_turn("Hello", "Hi there!", "assistant")
        context.add_turn("How are you?", "I'm doing well!", "assistant")

        result = context.get_recent_context()

        assert "User: Hello" in result
        assert "Agent (assistant): Hi there!" in result
        assert "User: How are you?" in result
        assert "Agent (assistant): I'm doing well!" in result

    def test_get_recent_context_limits_to_n_turns(self):
        """Test get_recent_context limits to n most recent turns."""
        context = ConversationContext()
        context.add_turn("q1", "r1", "agent")
        context.add_turn("q2", "r2", "agent")
        context.add_turn("q3", "r3", "agent")
        context.add_turn("q4", "r4", "agent")

        result = context.get_recent_context(n=2)

        assert "User: q1" not in result
        assert "User: q2" not in result
        assert "User: q3" in result
        assert "User: q4" in result

    def test_get_recent_context_with_empty_turns(self):
        """Test get_recent_context with no turns."""
        context = ConversationContext()
        result = context.get_recent_context()
        assert result == ""

    def test_should_continue_with_agent_returns_none_when_no_history(self):
        """Test follow-up detection returns None with no history."""
        context = ConversationContext()
        assert context.should_continue_with_agent("what about email?") is None

    def test_should_continue_with_agent_detects_follow_up_phrases(self):
        """Test follow-up detection for common follow-up phrases."""
        context = ConversationContext()
        context.add_turn("Check my email", "You have 3 emails", "gmail")

        follow_up_queries = [
            "what about unread ones?",
            "and also from John",
            "also check spam",
            "more about the first one",
            "tell me more",
            "can you show details?",
            "what else is there?",
            "anything else?",
        ]

        for query in follow_up_queries:
            result = context.should_continue_with_agent(query)
            assert result == "gmail", f"Failed for query: {query}"

    def test_should_continue_with_agent_detects_pronouns(self):
        """Test follow-up detection for short queries with pronouns."""
        context = ConversationContext()
        context.add_turn("Check my email", "You have 3 emails", "gmail")

        pronoun_queries = [
            "read it",
            "show them",
            "what's that?",
            "those ones",
            "this email",
        ]

        for query in pronoun_queries:
            result = context.should_continue_with_agent(query)
            assert result == "gmail", f"Failed for query: {query}"

    def test_should_continue_with_agent_returns_none_for_new_topics(self):
        """Test follow-up detection returns None for clearly new topics."""
        context = ConversationContext()
        context.add_turn("Check my email", "You have 3 emails", "gmail")

        new_topic_queries = [
            "What's the weather today?",
            "Set a reminder for tomorrow",
            "Play some music",
            "Search for restaurants nearby",
        ]

        for query in new_topic_queries:
            result = context.should_continue_with_agent(query)
            assert result is None, f"Should not follow-up for: {query}"


class TestConversationContextEdgeCases:
    """Additional edge case tests for ConversationContext."""

    def test_get_recent_context_with_many_turns(self):
        """Test get_recent_context performance with many turns."""
        context = ConversationContext()
        for i in range(100):
            context.add_turn(f"query_{i}", f"response_{i}", "agent")

        result = context.get_recent_context(n=5)

        # Should contain last 5 turns
        assert "query_95" in result
        assert "query_96" in result
        assert "query_97" in result
        assert "query_98" in result
        assert "query_99" in result
        # Should not contain earlier turns
        assert "query_94" not in result

    def test_should_continue_with_agent_case_sensitivity(self):
        """Test follow-up detection with mixed case queries."""
        context = ConversationContext()
        context.add_turn("Check email", "You have 3 emails", "gmail")

        # Mixed case should still work
        result = context.should_continue_with_agent("WHAT ABOUT THEM?")
        assert result == "gmail"

    def test_add_turn_with_very_long_strings(self):
        """Test add_turn with very long query/response strings."""
        context = ConversationContext()
        long_query = "x" * 10000
        long_response = "y" * 10000

        context.add_turn(long_query, long_response, "agent")

        assert len(context.turns) == 1
        assert len(context.turns[0].query) == 10000
        assert len(context.turns[0].response) == 10000

    def test_context_with_special_characters(self):
        """Test context handling of special characters."""
        context = ConversationContext()
        special_query = "What about emails with 'quotes' and \"double quotes\"?"
        special_response = "Found emails: <html> & special chars \n\t"

        context.add_turn(special_query, special_response, "gmail")

        result = context.get_recent_context()
        assert special_query in result
        assert special_response in result

    def test_multiple_agents_in_conversation(self):
        """Test context with multiple different agents."""
        context = ConversationContext()
        context.add_turn("Check email", "You have 3 emails", "gmail")
        context.add_turn("What's the weather?", "It's sunny", "weather")
        context.add_turn("Read the first email", "Email content...", "gmail")

        # last_agent should be gmail
        assert context.last_agent == "gmail"

        # get_recent_context should include all agents
        result = context.get_recent_context()
        assert "Agent (gmail)" in result
        assert "Agent (weather)" in result

    def test_should_continue_with_none_for_long_specific_query(self):
        """Test that long specific queries are not treated as follow-ups."""
        context = ConversationContext()
        context.add_turn("Check email", "You have 3 emails", "gmail")

        # A long, specific query about a different topic (not starting with follow-up phrases)
        long_query = (
            "Schedule a meeting for next Tuesday "
            "at 3pm with the marketing team in the main conference room"
        )
        result = context.should_continue_with_agent(long_query)
        assert result is None

    def test_should_continue_with_follow_up_phrase_prefix(self):
        """Test that queries starting with follow-up phrases are detected."""
        context = ConversationContext()
        context.add_turn("Check email", "You have 3 emails", "gmail")

        # Queries starting with follow-up phrases should be detected
        follow_up_queries = [
            "Can you show me more?",
            "What about the unread ones?",
            "Also check the spam folder",
        ]

        for query in follow_up_queries:
            result = context.should_continue_with_agent(query)
            assert result == "gmail", f"Expected follow-up detection for: {query}"

    def test_empty_query_handling(self):
        """Test handling of empty string query."""
        context = ConversationContext()
        context.add_turn("Check email", "You have 3 emails", "gmail")

        result = context.should_continue_with_agent("")
        # Empty query should not trigger follow-up
        assert result is None

    def test_get_recent_context_n_greater_than_turns(self):
        """Test get_recent_context when n is greater than available turns."""
        context = ConversationContext()
        context.add_turn("q1", "r1", "agent")
        context.add_turn("q2", "r2", "agent")

        result = context.get_recent_context(n=10)

        # Should include all available turns
        assert "q1" in result
        assert "q2" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
