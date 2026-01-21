"""Promptfoo Python provider for routing evaluation.

This provider is called by promptfoo to get routing decisions.
"""

import asyncio
import json
from typing import Any

from shared import get_routing_decision


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
