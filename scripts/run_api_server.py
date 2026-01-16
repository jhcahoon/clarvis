#!/usr/bin/env python3
"""Entry point script for running the Clarvis API server."""

import argparse
import asyncio
import sys
from pathlib import Path

# Fix Windows asyncio subprocess support
# Must be set before any asyncio operations
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv


def main():
    """Run the Clarvis API server."""
    parser = argparse.ArgumentParser(description="Run the Clarvis API server")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )

    args = parser.parse_args()

    # Load environment variables
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")

    # Import uvicorn here to avoid import errors if not installed
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is required. Install it with: pip install uvicorn")
        sys.exit(1)

    print(f"Starting Clarvis API server on {args.host}:{args.port}")
    print(f"API docs available at: http://{args.host}:{args.port}/docs")

    uvicorn.run(
        "clarvis_agents.api.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
