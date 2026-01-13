"""Intent classification for fast code-based routing."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ClassificationResult:
    """Result of intent classification."""

    agent_name: Optional[str]
    confidence: float
    needs_llm_routing: bool
    matched_keywords: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)


class IntentClassifier:
    """Fast code-based intent classification.

    Uses keyword and regex pattern matching to route queries to agents.
    Falls back to LLM routing when confidence is below threshold.
    """

    AGENT_PATTERNS: dict[str, dict[str, list[str]]] = {
        "gmail": {
            "keywords": [
                "email",
                "emails",
                "inbox",
                "unread",
                "mail",
                "gmail",
                "message",
                "messages",
            ],
            "patterns": [
                r"\b(check|read|search|find|show|list|get)\b.*\b(email|emails|mail|inbox)\b",
                r"\b(email|mail)\b.*\b(from|to|about|subject)\b",
                r"\bunread\b.*\b(email|emails|mail|message|messages)\b",
                r"\b(email|emails|mail|message|messages)\b.*\bunread\b",
            ],
        },
        "calendar": {
            "keywords": [
                "calendar",
                "schedule",
                "meeting",
                "meetings",
                "appointment",
                "appointments",
                "event",
                "events",
            ],
            "patterns": [
                r"\b(check|show|list|what|when)\b.*\b(calendar|schedule|meeting|meetings|appointment)\b",
                r"\b(schedule|book|create)\b.*\b(meeting|appointment|event)\b",
                r"\b(meeting|meetings|appointment|appointments)\b.*\b(today|tomorrow|this week)\b",
            ],
        },
        "weather": {
            "keywords": [
                "weather",
                "temperature",
                "rain",
                "forecast",
                "sunny",
                "cloudy",
            ],
            "patterns": [
                r"\b(what|how|check)\b.*\b(weather|temperature|forecast)\b",
                r"\bwill it\b.*\b(rain|snow|be sunny)\b",
            ],
        },
    }

    # Scoring constants
    KEYWORD_SCORE_PER_MATCH = 0.2
    KEYWORD_SCORE_CAP = 0.6
    PATTERN_SCORE_PER_MATCH = 0.3
    PATTERN_SCORE_CAP = 0.6
    AMBIGUITY_MARGIN = 0.1

    def __init__(self, threshold: float = 0.7) -> None:
        """Initialize the classifier.

        Args:
            threshold: Minimum confidence score for code-based routing.
                       Below this threshold, LLM routing is triggered.
        """
        self.threshold = threshold
        self._compiled_patterns: dict[str, list[re.Pattern[str]]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        for agent_name, config in self.AGENT_PATTERNS.items():
            self._compiled_patterns[agent_name] = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in config.get("patterns", [])
            ]

    def _match_keywords(self, query: str) -> dict[str, tuple[float, list[str]]]:
        """Match keywords in the query.

        Args:
            query: The user's query string.

        Returns:
            Dict mapping agent_name -> (score, matched_keywords).
            Score is capped at KEYWORD_SCORE_CAP.
        """
        query_lower = query.lower()
        results: dict[str, tuple[float, list[str]]] = {}

        for agent_name, config in self.AGENT_PATTERNS.items():
            matched = []
            for keyword in config.get("keywords", []):
                # Use word boundary matching for keywords
                if re.search(rf"\b{re.escape(keyword)}\b", query_lower):
                    matched.append(keyword)

            score = min(
                len(matched) * self.KEYWORD_SCORE_PER_MATCH, self.KEYWORD_SCORE_CAP
            )
            results[agent_name] = (score, matched)

        return results

    def _match_patterns(self, query: str) -> dict[str, tuple[float, list[str]]]:
        """Match regex patterns in the query.

        Args:
            query: The user's query string.

        Returns:
            Dict mapping agent_name -> (score, matched_pattern_strings).
            Score is capped at PATTERN_SCORE_CAP.
        """
        results: dict[str, tuple[float, list[str]]] = {}

        for agent_name, patterns in self._compiled_patterns.items():
            matched = []
            for i, pattern in enumerate(patterns):
                if pattern.search(query):
                    # Store the original pattern string for debugging
                    original_pattern = self.AGENT_PATTERNS[agent_name]["patterns"][i]
                    matched.append(original_pattern)

            score = min(
                len(matched) * self.PATTERN_SCORE_PER_MATCH, self.PATTERN_SCORE_CAP
            )
            results[agent_name] = (score, matched)

        return results

    def classify(self, query: str) -> ClassificationResult:
        """Classify a query and determine the target agent.

        Classification algorithm:
        1. Keyword matching: +0.2 per keyword (max 0.6)
        2. Regex pattern matching: +0.3 per pattern (max 0.6)
        3. needs_llm_routing = True if confidence < threshold OR no clear winner

        Args:
            query: The user's query string.

        Returns:
            ClassificationResult with the best matching agent and confidence.
        """
        keyword_results = self._match_keywords(query)
        pattern_results = self._match_patterns(query)

        # Combine scores per agent
        agent_scores: dict[str, float] = {}
        agent_keywords: dict[str, list[str]] = {}
        agent_patterns: dict[str, list[str]] = {}

        for agent_name in self.AGENT_PATTERNS:
            keyword_score, keywords = keyword_results.get(agent_name, (0.0, []))
            pattern_score, patterns = pattern_results.get(agent_name, (0.0, []))

            # Total score capped at 1.0
            agent_scores[agent_name] = min(keyword_score + pattern_score, 1.0)
            agent_keywords[agent_name] = keywords
            agent_patterns[agent_name] = patterns

        # Find the best agent
        sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)

        if not sorted_agents or sorted_agents[0][1] == 0:
            # No matches at all
            return ClassificationResult(
                agent_name=None,
                confidence=0.0,
                needs_llm_routing=True,
                matched_keywords=[],
                matched_patterns=[],
            )

        best_agent, best_score = sorted_agents[0]

        # Check for ambiguity (second-best agent is too close)
        is_ambiguous = False
        if len(sorted_agents) > 1:
            second_score = sorted_agents[1][1]
            if second_score > 0 and (best_score - second_score) < self.AMBIGUITY_MARGIN:
                is_ambiguous = True

        # Determine if LLM routing is needed
        needs_llm = best_score < self.threshold or is_ambiguous

        return ClassificationResult(
            agent_name=best_agent if not is_ambiguous else None,
            confidence=best_score,
            needs_llm_routing=needs_llm,
            matched_keywords=agent_keywords.get(best_agent, []),
            matched_patterns=agent_patterns.get(best_agent, []),
        )
