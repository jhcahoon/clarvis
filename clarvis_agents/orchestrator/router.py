"""Hybrid router combining code-based and LLM routing for the orchestrator."""

import os
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic

from ..core import AgentRegistry, ConversationContext
from .classifier import ClassificationResult, IntentClassifier
from .config import OrchestratorConfig
from .prompts import (
    GREETING_PATTERNS,
    ROUTER_SYSTEM_PROMPT,
    THANKS_PATTERNS,
    format_agent_descriptions,
)


@dataclass
class RoutingDecision:
    """Result of the routing decision.

    Attributes:
        agent_name: Name of the agent to route to, or None if handle_directly=True.
        confidence: Confidence score for the routing decision (0.0 to 1.0).
        reasoning: Explanation of why this routing decision was made.
        handle_directly: If True, the orchestrator handles the query directly
            (e.g., for greetings, thanks, or simple questions).
    """

    agent_name: Optional[str]
    confidence: float
    reasoning: str
    handle_directly: bool = False


class IntentRouter:
    """Hybrid router combining code-based and LLM routing.

    Routing algorithm:
    1. Check for follow-up (context.should_continue_with_agent)
    2. Check for direct handling (greetings, thanks)
    3. Code-based fast path (classifier.classify)
    4. LLM routing if needs_llm_routing=True
    """

    def __init__(
        self,
        registry: AgentRegistry,
        config: OrchestratorConfig,
        classifier: Optional[IntentClassifier] = None,
        anthropic_client: Optional[Anthropic] = None,
    ) -> None:
        """Initialize the router.

        Args:
            registry: Agent registry for looking up available agents.
            config: Orchestrator configuration.
            classifier: Optional custom classifier. Defaults to IntentClassifier
                with threshold from config.
            anthropic_client: Optional Anthropic client for LLM routing.
                Defaults to creating one from ANTHROPIC_API_KEY env var.
        """
        self.registry = registry
        self.config = config
        self.classifier = classifier or IntentClassifier(
            threshold=config.code_routing_threshold
        )
        self._client = anthropic_client

    @property
    def client(self) -> Anthropic:
        """Lazy-load Anthropic client.

        Raises:
            ValueError: If ANTHROPIC_API_KEY environment variable is not set.
        """
        if self._client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            self._client = Anthropic(api_key=api_key)
        return self._client

    def _should_handle_directly(self, query: str) -> Optional[RoutingDecision]:
        """Check if query should be handled directly by orchestrator.

        Args:
            query: The user's query.

        Returns:
            RoutingDecision if should handle directly, None otherwise.
        """
        query_lower = query.lower().strip()

        # Check greetings
        for pattern in GREETING_PATTERNS:
            if query_lower.startswith(pattern) or query_lower == pattern:
                return RoutingDecision(
                    agent_name=None,
                    confidence=1.0,
                    reasoning=f"Greeting detected: '{pattern}'",
                    handle_directly=True,
                )

        # Check thanks
        for pattern in THANKS_PATTERNS:
            if pattern in query_lower:
                return RoutingDecision(
                    agent_name=None,
                    confidence=1.0,
                    reasoning=f"Thanks/acknowledgment detected: '{pattern}'",
                    handle_directly=True,
                )

        return None

    def _check_follow_up(
        self, query: str, context: Optional[ConversationContext]
    ) -> Optional[RoutingDecision]:
        """Check if query is a follow-up to continue with last agent.

        Args:
            query: The user's query.
            context: Conversation context (may be None).

        Returns:
            RoutingDecision if follow-up detected, None otherwise.
        """
        if not self.config.follow_up_detection:
            return None

        if context is None:
            return None

        follow_up_agent = context.should_continue_with_agent(query)
        if follow_up_agent is None:
            return None

        # Verify agent still exists in registry
        if self.registry.get(follow_up_agent) is None:
            return None

        return RoutingDecision(
            agent_name=follow_up_agent,
            confidence=0.9,  # High but not 1.0 since it's heuristic
            reasoning=f"Follow-up detected, continuing with {follow_up_agent}",
            handle_directly=False,
        )

    async def _llm_route(
        self,
        query: str,
        classification: ClassificationResult,
        context: Optional[ConversationContext],
    ) -> RoutingDecision:
        """Use LLM to route ambiguous queries.

        Args:
            query: The user's query.
            classification: Result from code-based classification.
            context: Conversation context for additional info.

        Returns:
            RoutingDecision from LLM analysis.
        """
        # Build prompt with agent descriptions
        capabilities = self.registry.get_all_capabilities()
        agent_descriptions = format_agent_descriptions(capabilities)

        system_prompt = ROUTER_SYSTEM_PROMPT.format(
            agent_descriptions=agent_descriptions
        )

        # Build user message
        user_message = f"Query: {query}"
        if context and context.turns:
            recent = context.get_recent_context(n=2)
            user_message = f"Recent conversation:\n{recent}\n\nNew query: {query}"

        # Add classification hints
        if classification.agent_name:
            user_message += (
                f"\n\nCode-based hint: Possibly {classification.agent_name} "
                f"(confidence: {classification.confidence:.2f})"
            )

        try:
            response = self.client.messages.create(
                model=self.config.router_model,
                max_tokens=150,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            # Extract text from the response content block
            content_block = response.content[0]
            response_text = getattr(content_block, "text", str(content_block))
            return self._parse_llm_response(response_text)

        except Exception as e:
            # Fallback: use code classification or handle directly
            return self._handle_llm_error(classification, str(e))

    def _parse_llm_response(self, response_text: str) -> RoutingDecision:
        """Parse the LLM response into a RoutingDecision.

        Expected format:
        AGENT: <agent_name or DIRECT>
        CONFIDENCE: <0.0 to 1.0>
        REASONING: <explanation>

        Args:
            response_text: Raw text response from LLM.

        Returns:
            Parsed RoutingDecision.
        """
        lines = response_text.strip().split("\n")

        agent_name: Optional[str] = None
        confidence: float = 0.5
        reasoning: str = "LLM routing"
        handle_directly: bool = False

        for line in lines:
            line = line.strip()
            if line.upper().startswith("AGENT:"):
                agent_value = line[6:].strip()
                if agent_value.upper() == "DIRECT":
                    handle_directly = True
                    agent_name = None
                else:
                    agent_name = agent_value.lower()
            elif line.upper().startswith("CONFIDENCE:"):
                try:
                    confidence = float(line[11:].strip())
                    confidence = max(0.0, min(1.0, confidence))  # Clamp
                except ValueError:
                    confidence = 0.5
            elif line.upper().startswith("REASONING:"):
                reasoning = line[10:].strip()

        # Validate agent exists
        if agent_name and self.registry.get(agent_name) is None:
            # Agent doesn't exist, handle directly
            handle_directly = True
            agent_name = None
            reasoning = "LLM suggested unknown agent, handling directly"

        return RoutingDecision(
            agent_name=agent_name,
            confidence=confidence,
            reasoning=reasoning,
            handle_directly=handle_directly,
        )

    def _handle_llm_error(
        self, classification: ClassificationResult, error: str
    ) -> RoutingDecision:
        """Handle LLM routing errors gracefully.

        Falls back to code classification or direct handling.

        Args:
            classification: The code-based classification result.
            error: Error message from LLM call.

        Returns:
            Fallback RoutingDecision.
        """
        if classification.agent_name and classification.confidence > 0.3:
            # Use code classification as fallback
            return RoutingDecision(
                agent_name=classification.agent_name,
                confidence=classification.confidence,
                reasoning=f"LLM fallback due to error: {error}. Using code classification.",
                handle_directly=False,
            )

        # No good match, handle directly
        return RoutingDecision(
            agent_name=None,
            confidence=0.0,
            reasoning=f"LLM error ({error}), no confident match from code classification",
            handle_directly=True,
        )

    async def route(
        self, query: str, context: Optional[ConversationContext] = None
    ) -> RoutingDecision:
        """Route a query to the appropriate agent.

        Routing algorithm:
        1. Check for follow-up (context.should_continue_with_agent)
        2. Check for direct handling (greetings, thanks)
        3. Code-based fast path (classifier.classify)
        4. LLM routing if needs_llm_routing=True

        Args:
            query: The user's query.
            context: Optional conversation context.

        Returns:
            RoutingDecision indicating where to route.
        """
        # Step 1: Check for follow-up
        follow_up = self._check_follow_up(query, context)
        if follow_up is not None:
            return follow_up

        # Step 2: Check for direct handling
        direct = self._should_handle_directly(query)
        if direct is not None:
            return direct

        # Step 3: Code-based classification
        classification = self.classifier.classify(query)

        # If high confidence and LLM not needed, return immediately
        if not classification.needs_llm_routing:
            return RoutingDecision(
                agent_name=classification.agent_name,
                confidence=classification.confidence,
                reasoning=f"Code-based routing: matched keywords {classification.matched_keywords}",
                handle_directly=False,
            )

        # Step 4: LLM routing for ambiguous cases
        if self.config.llm_routing_enabled:
            return await self._llm_route(query, classification, context)

        # LLM disabled but routing needed - use best-effort code classification
        if classification.agent_name:
            return RoutingDecision(
                agent_name=classification.agent_name,
                confidence=classification.confidence,
                reasoning="LLM disabled, using low-confidence code match",
                handle_directly=False,
            )

        # No match at all
        return RoutingDecision(
            agent_name=None,
            confidence=0.0,
            reasoning="No agent match found, handling directly",
            handle_directly=True,
        )
