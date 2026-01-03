#!/usr/bin/env python3
"""Final test after running from terminal instead of IDE."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from clarvis_agents.gmail_agent import create_gmail_agent

# Load environment variables
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

async def test_agent():
    """Test the Gmail agent."""
    print("Creating Gmail agent...")
    agent = create_gmail_agent()

    print("\nTesting query: 'How many unread emails do I have?'\n")
    print("=" * 60)

    # Use the async method
    response = await agent._check_emails_async("How many unread emails do I have?")

    print("\nAgent Response:")
    print("=" * 60)
    print(response)
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_agent())
