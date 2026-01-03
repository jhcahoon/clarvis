#!/usr/bin/env python3
"""Quick test to verify Gmail agent works after config fix."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from clarvis_agents.gmail_agent import create_gmail_agent

# Load environment variables
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

async def test_gmail_agent():
    """Test Gmail agent with a simple query."""
    print("Creating Gmail agent...")
    agent = create_gmail_agent()

    print("Testing Gmail access with query: 'How many unread emails do I have?'\n")

    # Use the async method directly
    response = await agent._check_emails_async("How many unread emails do I have?")

    print("Agent Response:")
    print("-" * 60)
    print(response)
    print("-" * 60)
    print("\n✅ Gmail agent test completed!")

if __name__ == "__main__":
    asyncio.run(test_gmail_agent())
