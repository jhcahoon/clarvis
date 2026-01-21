#!/usr/bin/env python
"""Promptfoo provider that returns routing decisions as JSON.

This script serves as a bridge between promptfoo and the Clarvis router.
It accepts a query as a command-line argument (for promptfoo) or from stdin,
runs it through the IntentRouter, and outputs a JSON object with the routing
decision.

Usage (stdin - for manual testing):
    echo "check my email" | python evals/run_router.py
    echo "hello" | python evals/run_router.py
    echo "what about tomorrow?" | python evals/run_router.py --context '{"last_agent": "ski"}'

Usage (args - used by promptfoo):
    python evals/run_router.py "check my email"
    python evals/run_router.py "hello"
"""

import argparse
import asyncio
import json
import sys
from typing import Optional

# Add project root to path
sys.path.insert(0, ".")

from clarvis_agents.core import (
    AgentCapability,
    AgentRegistry,
    AgentResponse,
    BaseAgent,
    ConversationContext,
    ConversationTurn,
)
from clarvis_agents.orchestrator.config import OrchestratorConfig
from clarvis_agents.orchestrator.router import IntentRouter


class MockAgent(BaseAgent):
    """Mock agent for testing routing without real agent dependencies."""

    def __init__(self, name: str, description: str, capabilities: list[str]) -> None:
        """Initialize the mock agent.

        Args:
            name: Unique agent name (e.g., "gmail", "ski", "notes").
            description: Human-readable description.
            capabilities: List of capability names.
        """
        self._name = name
        self._description = description
        self._capabilities = [
            AgentCapability(
                name=cap,
                description=f"{cap} capability",
                keywords=[],
                examples=[],
            )
            for cap in capabilities
        ]

    @property
    def name(self) -> str:
        """Return the agent name."""
        return self._name

    @property
    def description(self) -> str:
        """Return the agent description."""
        return self._description

    @property
    def capabilities(self) -> list[AgentCapability]:
        """Return the agent capabilities."""
        return self._capabilities

    async def process(
        self, query: str, context: Optional[ConversationContext] = None
    ) -> AgentResponse:
        """Return a mock response."""
        return AgentResponse(
            content="mock response",
            success=True,
            agent_name=self._name,
        )

    def health_check(self) -> bool:
        """Return True (mock is always healthy)."""
        return True


def setup_registry() -> AgentRegistry:
    """Set up the agent registry with mock agents matching production setup.

    Returns:
        AgentRegistry populated with mock agents.
    """
    registry = AgentRegistry()
    registry.clear()

    # Register mock agents matching the production setup
    registry.register(
        MockAgent(
            "gmail",
            "Email agent for managing Gmail inbox",
            ["check_inbox", "search_emails", "read_email", "summarize"],
        )
    )
    registry.register(
        MockAgent(
            "ski",
            "Ski conditions agent for Mt Hood Meadows",
            ["snow_conditions", "lift_status", "weather", "full_report"],
        )
    )
    registry.register(
        MockAgent(
            "notes",
            "Notes agent for lists, reminders, and quick notes",
            ["manage_lists", "reminders", "notes", "list_management"],
        )
    )

    return registry


def parse_context(context_json: Optional[str]) -> Optional[ConversationContext]:
    """Parse a JSON context string into a ConversationContext object.

    Args:
        context_json: JSON string with context data, or None.

    Returns:
        ConversationContext if context_json is provided and valid, None otherwise.
    """
    if not context_json:
        return None

    try:
        ctx_data = json.loads(context_json)
    except json.JSONDecodeError:
        return None

    # Empty context object
    if not ctx_data:
        return None

    context = ConversationContext(session_id="test")
    context.last_agent = ctx_data.get("last_agent")

    for turn in ctx_data.get("turns", []):
        context.turns.append(
            ConversationTurn(
                query=turn.get("query", ""),
                response=turn.get("response", ""),
                agent_used=turn.get("agent_used", ""),
            )
        )

    return context


async def get_routing_decision(
    query: str, enable_llm: bool = False, context_json: Optional[str] = None
) -> dict:
    """Run the router and return the routing decision as a dict.

    Args:
        query: The user query to route.
        enable_llm: If True, enable LLM routing for ambiguous queries.
        context_json: Optional JSON string with conversation context.

    Returns:
        Dict with routing decision fields.
    """
    registry = setup_registry()

    config = OrchestratorConfig(
        llm_routing_enabled=enable_llm,
        code_routing_threshold=0.7,
        follow_up_detection=True,
    )

    router = IntentRouter(registry, config)
    context = parse_context(context_json)
    decision = await router.route(query, context=context)

    return {
        "agent_name": decision.agent_name,
        "confidence": decision.confidence,
        "reasoning": decision.reasoning,
        "handle_directly": decision.handle_directly,
    }


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Run the Clarvis router on a query"
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="The query to route (reads from stdin if not provided)",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable LLM routing for ambiguous queries",
    )
    parser.add_argument(
        "--context",
        type=str,
        default=None,
        help="JSON context for follow-up detection tests",
    )

    # Parse known args to handle extra args from promptfoo
    args, _ = parser.parse_known_args()

    # Get query from argument or stdin
    if args.query:
        query = args.query
    else:
        query = sys.stdin.read().strip()

    # Run the router
    result = asyncio.run(get_routing_decision(query, args.llm, args.context))

    # Output as JSON
    print(json.dumps(result))


if __name__ == "__main__":
    main()
