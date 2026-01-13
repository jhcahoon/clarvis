"""System prompts for the orchestrator router."""

from typing import Any

ROUTER_SYSTEM_PROMPT = """You are a routing assistant for a multi-agent home automation system.
Your job is to analyze user queries and determine which specialist agent should handle them.

AVAILABLE AGENTS:
{agent_descriptions}

ROUTING RULES:
1. Route to an agent ONLY if the query clearly matches their capabilities
2. Set AGENT: DIRECT for:
   - Greetings ("hello", "hi", "hey", "good morning")
   - Thanks ("thank you", "thanks")
   - Simple questions about yourself or the system
   - General conversation that doesn't require specialized agents
3. If uncertain between agents, choose the most likely one with lower confidence
4. Consider conversation context when routing follow-ups

RESPONSE FORMAT:
You MUST respond in this exact format (one item per line):
AGENT: <agent_name or DIRECT>
CONFIDENCE: <0.0 to 1.0>
REASONING: <brief one-line explanation>

Examples:
- For "check my emails": AGENT: gmail
- For "hello there": AGENT: DIRECT
- For "what's on my calendar": AGENT: calendar
"""

GREETING_PATTERNS = [
    "hello",
    "hi",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "howdy",
    "greetings",
    "yo",
    "hiya",
]

THANKS_PATTERNS = [
    "thank you",
    "thanks",
    "thx",
    "appreciate it",
    "cheers",
    "thank u",
    "ty",
]


def format_agent_descriptions(registry_capabilities: dict[str, list[Any]]) -> str:
    """Format agent capabilities for the router prompt.

    Args:
        registry_capabilities: Dict from AgentRegistry.get_all_capabilities().
            Keys are agent names, values are lists of AgentCapability objects.

    Returns:
        Formatted string describing each agent and its capabilities.
    """
    if not registry_capabilities:
        return "No agents currently available."

    lines = []
    for agent_name, capabilities in registry_capabilities.items():
        lines.append(f"Agent: {agent_name}")

        if capabilities:
            for cap in capabilities:
                lines.append(f"  - {cap.name}: {cap.description}")

            # Include first 2 examples from the first capability
            if capabilities[0].examples:
                examples = capabilities[0].examples[:2]
                lines.append(f"  Example queries: {', '.join(examples)}")
        else:
            lines.append("  - (No capabilities defined)")

        lines.append("")  # Blank line between agents

    return "\n".join(lines)
