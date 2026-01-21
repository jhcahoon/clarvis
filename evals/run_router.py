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

from shared import get_routing_decision


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
