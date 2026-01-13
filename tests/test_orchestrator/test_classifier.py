"""Tests for IntentClassifier and ClassificationResult (Issue #18)."""

import pytest

from clarvis_agents.orchestrator import (
    ClassificationResult,
    IntentClassifier,
)


class TestClassificationResult:
    """Test suite for ClassificationResult dataclass."""

    def test_result_with_required_fields(self):
        """Test ClassificationResult with required fields."""
        result = ClassificationResult(
            agent_name="gmail",
            confidence=0.8,
            needs_llm_routing=False,
        )
        assert result.agent_name == "gmail"
        assert result.confidence == 0.8
        assert result.needs_llm_routing is False

    def test_result_defaults_to_empty_lists(self):
        """Test that keyword and pattern lists default to empty."""
        result = ClassificationResult(
            agent_name="gmail",
            confidence=0.8,
            needs_llm_routing=False,
        )
        assert result.matched_keywords == []
        assert result.matched_patterns == []

    def test_result_with_all_fields(self):
        """Test ClassificationResult with all fields specified."""
        result = ClassificationResult(
            agent_name="gmail",
            confidence=0.9,
            needs_llm_routing=False,
            matched_keywords=["email", "inbox"],
            matched_patterns=[r"\b(check|read)\b.*\b(email)\b"],
        )
        assert result.agent_name == "gmail"
        assert result.confidence == 0.9
        assert result.needs_llm_routing is False
        assert result.matched_keywords == ["email", "inbox"]
        assert len(result.matched_patterns) == 1

    def test_result_with_none_agent(self):
        """Test ClassificationResult when no agent matches (ambiguous)."""
        result = ClassificationResult(
            agent_name=None,
            confidence=0.5,
            needs_llm_routing=True,
        )
        assert result.agent_name is None
        assert result.needs_llm_routing is True

    def test_result_confidence_bounds(self):
        """Test that confidence can be set to boundary values."""
        result_zero = ClassificationResult(
            agent_name=None,
            confidence=0.0,
            needs_llm_routing=True,
        )
        assert result_zero.confidence == 0.0

        result_one = ClassificationResult(
            agent_name="gmail",
            confidence=1.0,
            needs_llm_routing=False,
        )
        assert result_one.confidence == 1.0


class TestIntentClassifier:
    """Test suite for IntentClassifier."""

    def test_init_default_threshold(self):
        """Test that default threshold is 0.7."""
        classifier = IntentClassifier()
        assert classifier.threshold == 0.7

    def test_init_custom_threshold(self):
        """Test custom threshold initialization."""
        classifier = IntentClassifier(threshold=0.5)
        assert classifier.threshold == 0.5

    def test_agent_patterns_structure(self):
        """Test that AGENT_PATTERNS has expected structure."""
        classifier = IntentClassifier()

        # Check expected agents exist
        assert "gmail" in classifier.AGENT_PATTERNS
        assert "calendar" in classifier.AGENT_PATTERNS
        assert "weather" in classifier.AGENT_PATTERNS

        # Check each agent has keywords and patterns
        for agent_name, config in classifier.AGENT_PATTERNS.items():
            assert "keywords" in config, f"{agent_name} missing keywords"
            assert "patterns" in config, f"{agent_name} missing patterns"
            assert isinstance(config["keywords"], list)
            assert isinstance(config["patterns"], list)

    def test_patterns_are_compiled(self):
        """Test that patterns are pre-compiled."""
        classifier = IntentClassifier()
        assert len(classifier._compiled_patterns) > 0
        for patterns in classifier._compiled_patterns.values():
            for pattern in patterns:
                assert hasattr(pattern, "search"), "Pattern should be compiled regex"

    # Keyword matching tests
    def test_keyword_matching_single_keyword(self):
        """Test matching a single keyword."""
        classifier = IntentClassifier()
        results = classifier._match_keywords("check my email")

        assert "gmail" in results
        score, keywords = results["gmail"]
        assert "email" in keywords
        assert score == pytest.approx(0.2)

    def test_keyword_matching_multiple_keywords(self):
        """Test matching multiple keywords."""
        classifier = IntentClassifier()
        results = classifier._match_keywords("check my unread emails in inbox")

        score, keywords = results["gmail"]
        assert "unread" in keywords
        assert "emails" in keywords
        assert "inbox" in keywords
        assert score == pytest.approx(0.6)  # 3 keywords = 0.6 (capped)

    def test_keyword_matching_caps_at_06(self):
        """Test that keyword score caps at 0.6."""
        classifier = IntentClassifier()
        # Query with many gmail keywords
        results = classifier._match_keywords(
            "check my unread emails messages mail inbox gmail"
        )

        score, keywords = results["gmail"]
        assert score == pytest.approx(0.6)
        assert len(keywords) > 3  # More than 3 keywords matched

    def test_keyword_matching_case_insensitive(self):
        """Test that keyword matching is case insensitive."""
        classifier = IntentClassifier()

        results_lower = classifier._match_keywords("check my email")
        results_upper = classifier._match_keywords("CHECK MY EMAIL")
        results_mixed = classifier._match_keywords("Check My Email")

        assert results_lower["gmail"][0] == results_upper["gmail"][0]
        assert results_lower["gmail"][0] == results_mixed["gmail"][0]

    def test_keyword_matching_word_boundaries(self):
        """Test that keywords match on word boundaries."""
        classifier = IntentClassifier()

        # "email" should match
        results = classifier._match_keywords("send an email")
        assert "email" in results["gmail"][1]

        # "emailer" should NOT match "email"
        results = classifier._match_keywords("use the emailer tool")
        assert "email" not in results["gmail"][1]

    # Pattern matching tests
    def test_pattern_matching_single_pattern(self):
        """Test matching a single pattern."""
        classifier = IntentClassifier()
        results = classifier._match_patterns("check my email")

        score, patterns = results["gmail"]
        assert score == pytest.approx(0.3)
        assert len(patterns) == 1

    def test_pattern_matching_multiple_patterns(self):
        """Test matching multiple patterns."""
        classifier = IntentClassifier()
        results = classifier._match_patterns("check my unread email from john")

        score, patterns = results["gmail"]
        # Should match both "check...email" and "email...from" patterns
        assert score >= 0.3  # At least one pattern

    def test_pattern_matching_caps_at_06(self):
        """Test that pattern score caps at 0.6."""
        classifier = IntentClassifier()
        # This would match multiple patterns if we had enough
        results = classifier._match_patterns(
            "check my unread email messages from inbox"
        )

        score, _ = results["gmail"]
        assert score <= 0.6

    def test_pattern_matching_case_insensitive(self):
        """Test that pattern matching is case insensitive."""
        classifier = IntentClassifier()

        results_lower = classifier._match_patterns("check my email")
        results_upper = classifier._match_patterns("CHECK MY EMAIL")

        assert results_lower["gmail"][0] == results_upper["gmail"][0]

    # classify() method tests
    def test_classify_gmail_high_confidence(self):
        """Test high confidence classification for gmail."""
        classifier = IntentClassifier()
        # "check my unread emails" - keywords: emails, unread (0.4) + pattern match (0.3) = 0.7
        result = classifier.classify("check my unread emails")

        assert result.agent_name == "gmail"
        assert result.confidence >= 0.7
        assert result.needs_llm_routing is False

    def test_classify_calendar_high_confidence(self):
        """Test high confidence classification for calendar."""
        classifier = IntentClassifier()
        # "what meetings do I have today" - keywords: meetings (0.2) + patterns (0.3+0.3) = 0.8
        result = classifier.classify("what meetings do I have today")

        assert result.agent_name == "calendar"
        assert result.confidence >= 0.7
        assert result.needs_llm_routing is False

    def test_classify_weather_high_confidence(self):
        """Test high confidence classification for weather."""
        classifier = IntentClassifier()
        result = classifier.classify("what's the weather forecast")

        assert result.agent_name == "weather"
        assert result.confidence >= 0.7
        assert result.needs_llm_routing is False

    def test_classify_low_confidence_needs_llm(self):
        """Test that low confidence triggers LLM routing."""
        classifier = IntentClassifier()
        result = classifier.classify("help me with something")

        assert result.confidence < 0.7
        assert result.needs_llm_routing is True

    def test_classify_no_matches_needs_llm(self):
        """Test that queries with no matches need LLM routing."""
        classifier = IntentClassifier()
        result = classifier.classify("hello there")

        assert result.agent_name is None
        assert result.confidence == 0.0
        assert result.needs_llm_routing is True

    def test_classify_ambiguous_needs_llm(self):
        """Test that ambiguous queries trigger LLM routing."""
        classifier = IntentClassifier()
        # Query mentions both email and calendar with similar weight
        result = classifier.classify("email about meeting schedule")

        # Should flag as needing LLM routing due to ambiguity
        assert result.needs_llm_routing is True
        # When ambiguous, agent_name should be None and lists should be empty
        assert result.agent_name is None
        assert result.matched_keywords == []
        assert result.matched_patterns == []

    def test_classify_returns_matched_keywords(self):
        """Test that classification returns matched keywords."""
        classifier = IntentClassifier()
        result = classifier.classify("check my unread emails")

        assert len(result.matched_keywords) > 0
        assert "emails" in result.matched_keywords or "unread" in result.matched_keywords

    def test_classify_returns_matched_patterns(self):
        """Test that classification returns matched patterns."""
        classifier = IntentClassifier()
        result = classifier.classify("check my email")

        assert len(result.matched_patterns) > 0

    def test_classify_with_custom_threshold(self):
        """Test classification with custom threshold."""
        # Low threshold - single keyword "email" scores 0.2
        classifier_low = IntentClassifier(threshold=0.2)
        result_low = classifier_low.classify("email")
        # With threshold 0.2 and score 0.2, should not need LLM
        assert result_low.agent_name == "gmail"
        assert result_low.confidence == pytest.approx(0.2)
        assert result_low.needs_llm_routing is False

        # Higher threshold - single keyword not enough
        classifier_high = IntentClassifier(threshold=0.5)
        result_high = classifier_high.classify("email")
        # Score is 0.2, below 0.5 threshold
        assert result_high.agent_name == "gmail"
        assert result_high.needs_llm_routing is True


class TestIntentClassifierEdgeCases:
    """Additional edge case tests for IntentClassifier."""

    def test_classify_empty_query(self):
        """Test classification with empty query string."""
        classifier = IntentClassifier()
        result = classifier.classify("")

        assert result.agent_name is None
        assert result.confidence == 0.0
        assert result.needs_llm_routing is True

    def test_classify_whitespace_only_query(self):
        """Test classification with whitespace-only query."""
        classifier = IntentClassifier()
        result = classifier.classify("   \t\n   ")

        assert result.agent_name is None
        assert result.needs_llm_routing is True

    def test_classify_very_long_query(self):
        """Test classification with very long query string."""
        classifier = IntentClassifier()
        long_query = "check my email " * 100
        result = classifier.classify(long_query)

        assert result.agent_name == "gmail"
        assert result.confidence > 0

    def test_classify_special_characters(self):
        """Test classification with special characters in query."""
        classifier = IntentClassifier()
        result = classifier.classify("check email!!! @#$%")

        # Should still match email keywords
        assert result.agent_name == "gmail" or result.needs_llm_routing

    def test_match_keywords_partial_word(self):
        """Test that partial words don't match keywords."""
        classifier = IntentClassifier()
        results = classifier._match_keywords("emailer software")

        # "emailer" should not match "email" keyword
        score, keywords = results["gmail"]
        assert "email" not in keywords

    def test_ambiguity_detection_threshold(self):
        """Test the AMBIGUITY_MARGIN constant behavior."""
        classifier = IntentClassifier()
        # Query that mentions both email and calendar - calendar wins due to more matches
        result = classifier.classify("schedule email meeting calendar")

        # Calendar wins with higher confidence due to multiple keyword matches
        assert result.agent_name == "calendar"
        assert result.confidence >= 0.7

    def test_truly_ambiguous_query(self):
        """Test a query that triggers ambiguity detection."""
        classifier = IntentClassifier()
        # This query might be ambiguous between email and calendar
        result = classifier.classify("email about meeting")

        # Should be flagged as ambiguous when scores are close
        assert result.needs_llm_routing is True

    def test_classify_single_word_queries(self):
        """Test classification with single word queries."""
        classifier = IntentClassifier()

        # Single keyword should work
        result = classifier.classify("email")
        assert result.agent_name == "gmail"
        assert result.confidence == pytest.approx(0.2)

        result = classifier.classify("weather")
        assert result.agent_name == "weather"

        result = classifier.classify("calendar")
        assert result.agent_name == "calendar"

    def test_classify_punctuation_only(self):
        """Test classification with punctuation-only query."""
        classifier = IntentClassifier()
        result = classifier.classify("!@#$%^&*()")

        assert result.agent_name is None
        assert result.confidence == 0.0
        assert result.needs_llm_routing is True

    def test_classify_numeric_query(self):
        """Test classification with numeric query."""
        classifier = IntentClassifier()
        result = classifier.classify("12345")

        assert result.agent_name is None
        assert result.needs_llm_routing is True

    def test_classify_unicode_query(self):
        """Test classification with unicode characters."""
        classifier = IntentClassifier()
        result = classifier.classify("check my email \u00e9\u00e8\u00ea")

        # Should still match email keywords
        assert result.agent_name == "gmail"

    def test_keyword_matching_with_plurals(self):
        """Test that both singular and plural forms are matched."""
        classifier = IntentClassifier()

        # Test singular
        result_singular = classifier.classify("email")
        assert "email" in result_singular.matched_keywords or \
               result_singular.agent_name == "gmail"

        # Test plural
        result_plural = classifier.classify("emails")
        assert "emails" in result_plural.matched_keywords or \
               result_plural.agent_name == "gmail"

    def test_multiple_agents_clear_winner(self):
        """Test when one agent clearly wins over others."""
        classifier = IntentClassifier()
        # Very email-specific query
        result = classifier.classify("read my unread emails in inbox from john")

        assert result.agent_name == "gmail"
        assert result.needs_llm_routing is False
        assert result.confidence >= 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
