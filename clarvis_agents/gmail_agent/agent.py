"""Gmail Agent implementation using Claude Agent SDK."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from claude_agent_sdk import query, ClaudeAgentOptions, ClaudeSDKClient

from .config import GmailAgentConfig, RateLimiter
from .prompts import SYSTEM_PROMPT


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GmailAgent:
    """Gmail checking agent using Claude Agent SDK."""

    def __init__(self, config: Optional[GmailAgentConfig] = None):
        """
        Initialize Gmail Agent.

        Args:
            config: Configuration for the agent. If None, uses default config.
        """
        self.config = config or GmailAgentConfig()
        self._setup_logging()
        self.rate_limiter = RateLimiter(
            max_calls=self.config.max_searches_per_minute,
            time_window=timedelta(minutes=1)
        )

    def _setup_logging(self) -> None:
        """Configure audit logging for email access."""
        self.config.log_dir.mkdir(parents=True, exist_ok=True)

        log_file = self.config.log_dir / f"access_{datetime.now():%Y%m%d}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(file_handler)
        logger.info("Gmail Agent logging initialized")

    def _build_agent_options(self) -> ClaudeAgentOptions:
        """
        Build ClaudeAgentOptions with MCP servers and settings.

        Returns:
            Configured ClaudeAgentOptions for the query
        """
        # Get MCP configuration
        mcp_config = self.config.get_mcp_config()["gmail"]

        # Build options
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={
                "gmail": {
                    "type": mcp_config["type"],
                    "command": mcp_config["command"],
                    "args": mcp_config["args"],
                    "env": mcp_config.get("env", {}),
                },
                # Note: SDK MCP servers (gmail_helpers) don't work with CLI subprocess mode
                # The agent can construct Gmail queries without helper tools
            },
            model=self.config.model,
            max_turns=self.config.max_turns,
            # Skip permission checks for MCP tools - required for SDK MCP tool usage
            extra_args={"dangerously-skip-permissions": None},
        )

        return options

    async def _check_emails_async(self, query_text: str) -> str:
        """
        Single query without session context (for programmatic usage).

        This method uses stateless query() for one-off email checks.
        For interactive mode with context retention, use run_interactive() instead.

        Args:
            query_text: Natural language query about emails

        Returns:
            Agent's response as string
        """
        # Check rate limit
        if not self.rate_limiter.check_rate_limit():
            return "Rate limit exceeded. Please wait before making another request."

        # Log the query (audit trail)
        logger.info(f"Processing email query: {query_text[:100]}...")

        try:
            # Build agent options
            options = self._build_agent_options()

            # Stream response from Claude Agent SDK
            response_text = ""
            async for message in query(prompt=query_text, options=options):
                # Handle different message types
                if hasattr(message, 'result'):
                    # ResultMessage - final output
                    response_text += str(message.result)
                elif hasattr(message, 'text'):
                    # Text content
                    response_text += str(message.text)
                elif hasattr(message, 'content'):
                    # AssistantMessage with content blocks
                    if isinstance(message.content, str):
                        response_text += message.content
                    elif isinstance(message.content, list):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                response_text += block.text

            if not response_text:
                response_text = "I processed your request but couldn't generate a response."

            logger.info("Email query processed successfully")
            return response_text

        except Exception as e:
            logger.error(f"Error checking emails: {e}", exc_info=True)
            return f"Sorry, I encountered an error: {str(e)}"

    def check_emails(self, query: str) -> str:
        """
        Main entry point for checking emails (synchronous wrapper).

        Args:
            query: Natural language query about emails

        Returns:
            Agent's response as string
        """
        return asyncio.run(self._check_emails_async(query))

    async def run_interactive_async(self) -> None:
        """Run agent in interactive mode with context retention."""
        print("Gmail Agent started. Type 'quit' to exit.")
        print("Try: 'Check my unread emails' or 'Show emails from last week'\n")

        # Build options once for the session
        options = self._build_agent_options()

        # Create client with session context
        async with ClaudeSDKClient(options=options) as client:
            print("Session started. All queries in this session will have context.\n")

            while True:
                try:
                    user_input = input("You: ").strip()
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("Goodbye!")
                        break

                    if not user_input:
                        continue

                    # Check rate limit
                    if not self.rate_limiter.check_rate_limit():
                        print("\nRate limit exceeded. Please wait before making another request.\n")
                        continue

                    # Log query
                    logger.info(f"Processing email query: {user_input[:100]}...")

                    # Send query in existing session (Claude remembers previous context)
                    await client.query(user_input)

                    # Receive and display response
                    print("\nAgent: ", end="", flush=True)
                    async for message in client.receive_response():
                        if hasattr(message, 'content'):
                            if isinstance(message.content, str):
                                print(message.content, end="", flush=True)
                            elif isinstance(message.content, list):
                                for block in message.content:
                                    if hasattr(block, 'text'):
                                        print(block.text, end="", flush=True)
                    print("\n")

                    logger.info("Email query processed successfully")

                except KeyboardInterrupt:
                    print("\nGoodbye!")
                    break
                except Exception as e:
                    logger.error(f"Error in interactive mode: {e}", exc_info=True)
                    print(f"\nError: {e}\n")

    def run_interactive(self) -> None:
        """Run agent in interactive mode (synchronous wrapper)."""
        asyncio.run(self.run_interactive_async())


def create_gmail_agent(read_only: bool = True) -> GmailAgent:
    """
    Factory function to create Gmail agent.

    Args:
        read_only: If True, agent only has read permissions

    Returns:
        Configured GmailAgent instance
    """
    config = GmailAgentConfig(read_only=read_only)
    return GmailAgent(config)


# Main entry point for running as a module
if __name__ == "__main__":
    agent = create_gmail_agent()
    agent.run_interactive()
