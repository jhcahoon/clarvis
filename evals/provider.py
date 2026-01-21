"""Promptfoo Python provider for routing evaluation.

This provider is called by promptfoo to get routing decisions.
"""

import asyncio
import json
import os
import sys
from typing import Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

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
from typing import Optional


class MockAgent(BaseAgent):
    """Mock agent for testing routing without real agent dependencies."""

    def __init__(self, name: str, description: str, capabilities: list[str]) -> None:
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
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def capabilities(self) -> list[AgentCapability]:
        return self._capabilities

    async def process(
        self, query: str, context: Optional[ConversationContext] = None
    ) -> AgentResponse:
        return AgentResponse(
            content="mock response",
            success=True,
            agent_name=self._name,
        )

    def health_check(self) -> bool:
        return True


def setup_registry() -> AgentRegistry:
    """Set up the agent registry with mock agents."""
    registry = AgentRegistry()
    registry.clear()

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
    """Parse a JSON context string into a ConversationContext object."""
    if not context_json:
        return None

    try:
        ctx_data = json.loads(context_json)
    except json.JSONDecodeError:
        return None

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
) -> dict[str, Any]:
    """Run the router and return the routing decision."""
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


def call_api(prompt: str, options: dict, context: dict) -> dict[str, Any]:
    """Promptfoo provider entry point.

    Args:
        prompt: The prompt (query) to route.
        options: Provider options.
        context: Test context with vars.

    Returns:
        Dict with 'output' key containing the routing decision JSON.
    """
    # Get configuration from options or context
    vars_dict = context.get("vars", {})
    enable_llm = vars_dict.get("enable_llm", False)
    context_json = vars_dict.get("context")

    # Run the router
    result = asyncio.run(get_routing_decision(prompt, enable_llm, context_json))

    # Return as JSON string (promptfoo expects this format)
    return {"output": json.dumps(result)}
