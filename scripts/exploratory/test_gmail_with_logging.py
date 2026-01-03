#!/usr/bin/env python3
"""Test Gmail tools specifically with env logging."""

import asyncio
import glob
from pathlib import Path
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions

# Load environment variables
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

WRAPPER_SCRIPT = str(Path(__file__).parent / "mcp_env_logger.sh")

def stderr_handler(message: str) -> None:
    """Capture stderr for debugging."""
    # Filter for interesting messages
    if any(x in message.lower() for x in ['gmail', 'mcp', 'error', 'permission', 'auth', 'credential']):
        print(f"[STDERR] {message}")

async def test_gmail_tools():
    """Test actual Gmail tool usage."""

    print("=" * 70)
    print("Testing Gmail Tools with Environment Logging")
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
        system_prompt="You are a Gmail assistant. When asked about emails, use the Gmail search tool.",
        mcp_servers=mcp_config,
        model="claude-3-5-haiku-20241022",
        max_turns=10,
        stderr=stderr_handler,
    )

    print("\nQuery: 'How many unread emails do I have? Use the Gmail search tool.'\n")
    print("-" * 70)

    full_response = ""
    async for message in query(
        prompt="How many unread emails do I have? Use the Gmail search tool to find out.",
        options=options
    ):
        if hasattr(message, 'content'):
            if isinstance(message.content, str):
                full_response += message.content
                print(message.content, end="", flush=True)
            elif isinstance(message.content, list):
                for block in message.content:
                    if hasattr(block, 'text'):
                        full_response += block.text
                        print(block.text, end="", flush=True)

    print("\n" + "-" * 70)
    print("\n=== Analysis ===")

    if "permission" in full_response.lower() or "don't have" in full_response.lower():
        print("❌ FAILED: Agent still reports permission issues")
    elif "unread" in full_response.lower() and any(char.isdigit() for char in full_response):
        print("✅ SUCCESS: Agent appears to have accessed Gmail!")
    else:
        print("⚠️ UNCLEAR: Check response above for details")

    # Check log files
    print("\n=== Latest MCP Log ===")
    log_files = sorted(glob.glob("/tmp/mcp_env_debug_*.log"), reverse=True)
    if log_files:
        with open(log_files[0], 'r') as f:
            content = f.read()
            # Just show Gmail-specific part
            if "Gmail-Specific" in content:
                start = content.find("=== Gmail-Specific")
                print(content[start:start+300])

if __name__ == "__main__":
    asyncio.run(test_gmail_tools())
