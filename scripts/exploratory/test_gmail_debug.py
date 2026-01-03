#!/usr/bin/env python3
"""Debug test to see actual MCP server errors."""

import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from clarvis_agents.gmail_agent import GmailAgent, GmailAgentConfig

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

async def test_with_debug():
    """Test with full debug output."""
    print("Creating Gmail agent with debug logging...")

    config = GmailAgentConfig()

    # Print the MCP config being used
    mcp_config = config.get_mcp_config()
    print("\n" + "="*60)
    print("MCP Configuration:")
    print("="*60)
    import json
    print(json.dumps(mcp_config, indent=2))
    print("="*60 + "\n")

    agent = GmailAgent(config)

    print("Testing Gmail access...\n")
    response = await agent._check_emails_async("List my 3 most recent unread emails")

    print("\n" + "="*60)
    print("Agent Response:")
    print("="*60)
    print(response)
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_with_debug())
