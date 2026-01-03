"""Entry point for running Gmail Agent as a module."""

from pathlib import Path
from dotenv import load_dotenv

from .agent import create_gmail_agent


def main():
    """Main entry point for CLI."""
    # Load environment variables from .env file
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    agent = create_gmail_agent()
    agent.run_interactive()


if __name__ == "__main__":
    main()
