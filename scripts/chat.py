#!/usr/bin/env python3
"""Interactive CLI for querying the Clarvis API with streaming responses."""

import argparse
import json
import sys

import httpx


def stream_query(client: httpx.Client, base_url: str, query: str, session_id: str | None = None) -> str | None:
    """Send a query and stream the response. Returns the session_id."""
    payload = {"query": query}
    if session_id:
        payload["session_id"] = session_id

    returned_session_id = session_id

    try:
        with client.stream(
            "POST",
            f"{base_url}/api/v1/query/stream",
            json=payload,
            timeout=120.0,
        ) as response:
            if response.status_code != 200:
                print(f"\nError: {response.status_code}")
                return returned_session_id

            for line in response.iter_lines():
                if not line:
                    continue

                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix

                    if data == "[DONE]":
                        break

                    try:
                        parsed = json.loads(data)
                        if "text" in parsed:
                            print(parsed["text"], end="", flush=True)
                        if "session_id" in parsed and not returned_session_id:
                            returned_session_id = parsed["session_id"]
                    except json.JSONDecodeError:
                        # Not JSON, might be raw text
                        print(data, end="", flush=True)

    except httpx.ConnectError:
        print("\nError: Could not connect to the API server.")
        print("Make sure the server is running: python scripts/run_api_server.py")
    except httpx.ReadTimeout:
        print("\n[Response timed out]")

    return returned_session_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive CLI for Clarvis")
    parser.add_argument(
        "--host",
        default="localhost",
        help="API server host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API server port (default: 8000)",
    )
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"

    print("Clarvis CLI")
    print(f"Connected to {base_url}")
    print("Type 'quit' to exit, 'new' to start a new session\n")

    session_id = None

    with httpx.Client() as client:
        # Check server health
        try:
            health = client.get(f"{base_url}/health", timeout=5.0)
            if health.status_code == 200:
                data = health.json()
                agents = data.get("agents", {})
                available = [k for k, v in agents.items() if v == "available"]
                print(f"Available agents: {', '.join(available)}\n")
        except httpx.ConnectError:
            print("Warning: Could not connect to server. Is it running?\n")

        while True:
            try:
                query = input("You: ").strip()

                if not query:
                    continue

                if query.lower() in ("quit", "exit", "q"):
                    print("Goodbye!")
                    break

                if query.lower() == "new":
                    session_id = None
                    print("Started new session.\n")
                    continue

                print("\nClarvis: ", end="", flush=True)
                session_id = stream_query(client, base_url, query, session_id)
                print("\n")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except EOFError:
                print("\nGoodbye!")
                break


if __name__ == "__main__":
    main()
