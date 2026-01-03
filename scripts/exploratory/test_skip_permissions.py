#!/usr/bin/env python3
"""Test with permissions bypassed to confirm the root cause."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions

# Load environment variables
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

WRAPPER_SCRIPT = str(Path(__file__).parent / "mcp_env_logger.sh")

async def test_skip_permissions():
    """Test with dangerously-skip-permissions to confirm the fix."""

    print("=" * 70)
    print("Testing Gmail with --dangerously-skip-permissions")
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
        # Try to skip permissions
        extra_args={"dangerously-skip-permissions": None},
    )

    print("\nQuery: 'Search for unread emails'\n")
    print("-" * 70)

    message_count = 0
    async for message in query(
        prompt="Search for unread emails using the Gmail search tool.",
        options=options
    ):
        message_count += 1
        msg_type = type(message).__name__

        # Look for tool results
        if hasattr(message, 'content') and isinstance(message.content, list):
            for block in message.content:
                block_type = type(block).__name__
                if 'ToolResult' in block_type:
                    print(f"\n[TOOL RESULT]")
                    if hasattr(block, 'content'):
                        content = str(block.content)
                        print(f"  Content: {content[:500]}...")
                    if hasattr(block, 'is_error'):
                        print(f"  Is Error: {block.is_error}")
                elif 'TextBlock' in block_type:
                    if hasattr(block, 'text'):
                        print(block.text, end="", flush=True)

    print("\n" + "-" * 70)
    print(f"\nTotal messages: {message_count}")

if __name__ == "__main__":
    asyncio.run(test_skip_permissions())
