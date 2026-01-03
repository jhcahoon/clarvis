#!/usr/bin/env python3
"""Test to capture exactly what env vars reach the MCP server via SDK."""

import asyncio
import glob
import os
from pathlib import Path
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions

# Load environment variables
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Path to our wrapper script
WRAPPER_SCRIPT = str(Path(__file__).parent / "mcp_env_logger.sh")

async def test_with_env_logging():
    """Test SDK with env logging wrapper."""

    print("=" * 60)
    print("Testing SDK with Environment Variable Logging")
    print("=" * 60)
    print(f"\nWrapper script: {WRAPPER_SCRIPT}")
    print("\nMCP Config being sent to SDK:")

    # Build MCP config with wrapper script instead of npx
    mcp_config = {
        "gmail": {
            "type": "stdio",
            "command": WRAPPER_SCRIPT,  # Use our logging wrapper
            "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
            "env": {
                "GMAIL_OAUTH_PATH": "/Users/james.cahoon/.gmail-mcp/gcp-oauth.keys.json",
                "GMAIL_CREDENTIALS_PATH": "/Users/james.cahoon/.gmail-mcp/credentials.json",
            }
        }
    }

    import json
    print(json.dumps(mcp_config, indent=2))

    options = ClaudeAgentOptions(
        system_prompt="You are a helpful assistant with Gmail access.",
        mcp_servers=mcp_config,
        model="claude-3-5-haiku-20241022",
        max_turns=5,
    )

    print("\n" + "=" * 60)
    print("Running query (this will create a log file)...")
    print("=" * 60)

    try:
        async for message in query(prompt="List available tools", options=options):
            if hasattr(message, 'content'):
                if isinstance(message.content, str):
                    print(message.content[:200] + "..." if len(message.content) > 200 else message.content)
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("Checking log files...")
    print("=" * 60)

    # Find and display the log file
    log_files = sorted(glob.glob("/tmp/mcp_env_debug_*.log"), reverse=True)

    if log_files:
        latest_log = log_files[0]
        print(f"\nLatest log file: {latest_log}")
        print("\n--- Log Contents ---")
        with open(latest_log, 'r') as f:
            print(f.read())
    else:
        print("\nNo log file found! Wrapper may not have been executed.")

if __name__ == "__main__":
    asyncio.run(test_with_env_logging())
