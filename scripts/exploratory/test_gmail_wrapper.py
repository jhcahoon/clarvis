#!/usr/bin/env python3
"""Test with wrapper script to see actual env vars."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions
from clarvis_agents.gmail_agent.config import GmailAgentConfig
from clarvis_agents.gmail_agent.prompts import SYSTEM_PROMPT

# Load environment variables
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

def stderr_handler(message: str) -> None:
    """Capture stderr to see wrapper output."""
    print(f"[STDERR] {message}")

async def test_with_wrapper():
    """Test with wrapper script."""
    config = GmailAgentConfig()
    mcp_config = config.get_mcp_config()["gmail"]

    # Use wrapper script instead of npx directly
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={
            "gmail": {
                "type": "stdio",
                "command": str(Path(__file__).parent / "mcp_wrapper.sh"),  # Use wrapper
                "args": [],  # No args needed, wrapper calls npx
                "env": mcp_config["env"],  # Same env vars
            }
        },
        model=config.model,
        max_turns=5,
        stderr=stderr_handler,
    )

    print("Testing with wrapper script...")
    print("=" * 60)

    response_text = ""
    async for message in query(prompt="How many unread emails?", options=options):
        if hasattr(message, 'content'):
            if isinstance(message.content, str):
                response_text += message.content
            elif isinstance(message.content, list):
                for block in message.content:
                    if hasattr(block, 'text'):
                        response_text += block.text

    print("\n" + "=" * 60)
    print("Response:")
    print("=" * 60)
    print(response_text)
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_with_wrapper())
