#!/usr/bin/env python3
"""Test with hooks to capture tool results."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions

# Load environment variables
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

WRAPPER_SCRIPT = str(Path(__file__).parent / "mcp_env_logger.sh")

# Store tool results
tool_results = []

async def pre_tool_hook(
    input_data: Dict[str, Any],
    tool_use_id: str | None,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Log before tool execution."""
    tool_name = input_data.get('tool_name', 'unknown')
    tool_input = input_data.get('tool_input', {})

    print(f"\n{'='*60}")
    print(f"[PRE-TOOL] Tool: {tool_name}")
    print(f"[PRE-TOOL] ID: {tool_use_id}")
    print(f"[PRE-TOOL] Input: {json.dumps(tool_input, indent=2)}")
    print(f"{'='*60}\n")

    return {"continue_": True}

async def post_tool_hook(
    input_data: Dict[str, Any],
    tool_use_id: str | None,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Log after tool execution - THIS SHOULD SHOW THE ERROR!"""
    tool_name = input_data.get('tool_name', 'unknown')
    tool_response = input_data.get('tool_response', 'NO RESPONSE')

    print(f"\n{'='*60}")
    print(f"[POST-TOOL] Tool: {tool_name}")
    print(f"[POST-TOOL] ID: {tool_use_id}")
    print(f"[POST-TOOL] Response Type: {type(tool_response)}")
    print(f"[POST-TOOL] Response:")
    if isinstance(tool_response, dict):
        print(json.dumps(tool_response, indent=2))
    else:
        print(str(tool_response)[:500])
    print(f"{'='*60}\n")

    tool_results.append({
        'tool': tool_name,
        'id': tool_use_id,
        'response': tool_response
    })

    return {"continue_": True}

def stderr_handler(message: str) -> None:
    """Capture stderr."""
    if "error" in message.lower() or "gmail" in message.lower() or "mcp" in message.lower():
        print(f"[STDERR] {message}")

async def test_with_hooks():
    """Test Gmail with pre/post hooks to capture tool results."""

    print("=" * 70)
    print("Testing Gmail Tools with Pre/Post Hooks")
    print("=" * 70)

    # Try importing HookMatcher
    try:
        from claude_agent_sdk import HookMatcher
        print("✓ HookMatcher imported successfully")

        hooks_config = {
            "PreToolUse": [
                HookMatcher(
                    matcher="mcp__gmail__*",
                    hooks=[pre_tool_hook],
                    timeout=30.0
                )
            ],
            "PostToolUse": [
                HookMatcher(
                    matcher="mcp__gmail__*",
                    hooks=[post_tool_hook],
                    timeout=30.0
                )
            ],
        }
    except ImportError as e:
        print(f"✗ HookMatcher not available: {e}")
        hooks_config = {}

    mcp_config = {
        "gmail": {
            "type": "stdio",
            "command": WRAPPER_SCRIPT,
            "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
            "env": {
                "GMAIL_OAUTH_PATH": "/Users/james.cahoon/.gmail-mcp/gcp-oauth.keys.json",
                "GMAIL_CREDENTIALS_PATH": "/Users/james.cahoon/.gmail-mcp/credentials.json",
            }
        }
    }

    options = ClaudeAgentOptions(
        system_prompt="You are a Gmail assistant. Use Gmail tools to answer questions about emails.",
        mcp_servers=mcp_config,
        model="claude-3-5-haiku-20241022",
        max_turns=10,
        stderr=stderr_handler,
        hooks=hooks_config if hooks_config else None,
    )

    print("\nQuery: 'Search for unread emails using the Gmail search tool'\n")
    print("-" * 70)

    async for message in query(
        prompt="Search for unread emails using the Gmail search tool. Tell me what you find.",
        options=options
    ):
        if hasattr(message, 'content'):
            if isinstance(message.content, str):
                print(message.content, end="", flush=True)
            elif isinstance(message.content, list):
                for block in message.content:
                    if hasattr(block, 'text'):
                        print(block.text, end="", flush=True)

    print("\n" + "-" * 70)

    if tool_results:
        print("\n=== Captured Tool Results ===")
        for result in tool_results:
            print(f"\nTool: {result['tool']}")
            print(f"Response: {result['response']}")
    else:
        print("\n⚠️ No tool results captured by hooks")

if __name__ == "__main__":
    asyncio.run(test_with_hooks())
