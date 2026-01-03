#!/usr/bin/env python3
"""Test with stderr callback to see MCP server errors."""

import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions
from clarvis_agents.gmail_agent.config import GmailAgentConfig
from clarvis_agents.gmail_agent.prompts import SYSTEM_PROMPT

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Stderr callback to capture MCP server output
def stderr_handler(message: str) -> None:
    """Capture all stderr output from MCP server and CLI."""
    print(f"[STDERR] {message}")
    if "error" in message.lower() or "fail" in message.lower():
        print(f"[ERROR DETECTED] {message}")

async def test_with_stderr():
    """Test with stderr callback."""
    config = GmailAgentConfig()
    mcp_config = config.get_mcp_config()["gmail"]

    # Build options with stderr callback
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={
            "gmail": {
                "type": mcp_config["type"],
                "command": mcp_config["command"],
                "args": mcp_config["args"],
                "env": mcp_config["env"],
            }
        },
        model=config.model,
        max_turns=config.max_turns,
        stderr=stderr_handler,  # Capture stderr
        extra_args={"debug-to-stderr": None},  # Enable verbose output
    )

    print("Testing Gmail agent with stderr capture...")
    print("=" * 60)

    response_text = ""
    async for message in query(prompt="How many unread emails do I have?", options=options):
        if hasattr(message, 'content'):
            if isinstance(message.content, str):
                response_text += message.content
            elif isinstance(message.content, list):
                for block in message.content:
                    if hasattr(block, 'text'):
                        response_text += block.text

    print("\n" + "=" * 60)
    print("Agent Response:")
    print("=" * 60)
    print(response_text)
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_with_stderr())
