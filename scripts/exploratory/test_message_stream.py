#!/usr/bin/env python3
"""Inspect the actual message stream to find tool results."""

import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions

# Load environment variables
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

WRAPPER_SCRIPT = str(Path(__file__).parent / "mcp_env_logger.sh")

async def test_message_stream():
    """Inspect every message in the stream."""

    print("=" * 70)
    print("Inspecting Message Stream for Tool Results")
    print("=" * 70)

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
        system_prompt="You are a Gmail assistant. Use Gmail tools when asked about emails.",
        mcp_servers=mcp_config,
        model="claude-3-5-haiku-20241022",
        max_turns=10,
    )

    print("\nQuery: 'Use the search_emails tool to find unread emails'\n")
    print("-" * 70)

    message_count = 0
    async for message in query(
        prompt="Use the search_emails tool to find unread emails. Show me the raw result.",
        options=options
    ):
        message_count += 1
        msg_type = type(message).__name__

        print(f"\n[Message {message_count}] Type: {msg_type}")

        # Print all attributes
        for attr in dir(message):
            if not attr.startswith('_'):
                try:
                    value = getattr(message, attr)
                    if not callable(value):
                        # Truncate long values
                        str_value = str(value)
                        if len(str_value) > 200:
                            str_value = str_value[:200] + "..."
                        print(f"  .{attr} = {str_value}")
                except Exception as e:
                    print(f"  .{attr} = <error: {e}>")

        # Special handling for content blocks
        if hasattr(message, 'content'):
            content = message.content
            if isinstance(content, list):
                print(f"\n  Content Blocks ({len(content)}):")
                for i, block in enumerate(content):
                    block_type = type(block).__name__
                    print(f"    [{i}] {block_type}")

                    # Check for tool use/result blocks
                    if 'ToolUse' in block_type:
                        if hasattr(block, 'name'):
                            print(f"        name: {block.name}")
                        if hasattr(block, 'input'):
                            print(f"        input: {block.input}")
                        if hasattr(block, 'id'):
                            print(f"        id: {block.id}")

                    if 'ToolResult' in block_type:
                        if hasattr(block, 'tool_use_id'):
                            print(f"        tool_use_id: {block.tool_use_id}")
                        if hasattr(block, 'content'):
                            result_content = str(block.content)
                            if len(result_content) > 500:
                                result_content = result_content[:500] + "..."
                            print(f"        content: {result_content}")
                        if hasattr(block, 'is_error'):
                            print(f"        is_error: {block.is_error}")

    print("\n" + "-" * 70)
    print(f"\nTotal messages received: {message_count}")

if __name__ == "__main__":
    asyncio.run(test_message_stream())
