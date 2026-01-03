#!/usr/bin/env python3
"""
Test if Gmail MCP tools are actually available when launching via CLI.
"""

import subprocess
import json
import tempfile
import os

def test_gmail_tools_available():
    """Test if Gmail tools load when using CLI with MCP config."""

    print("=" * 80)
    print("TEST: Gmail MCP Tools via Claude CLI")
    print("=" * 80)

    # Create config with Gmail MCP server
    config = {
        "mcpServers": {
            "gmail": {
                "command": "npx",
                "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
                "env": {
                    "GMAIL_OAUTH_PATH": "/Users/james.cahoon/.gmail-mcp/gcp-oauth.keys.json",
                    "GMAIL_CREDENTIALS_PATH": "/Users/james.cahoon/.gmail-mcp/credentials.json"
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, indent=2)
        config_path = f.name

    # Ask specifically about Gmail tools
    test_prompts = [
        "List all tools that contain 'gmail' or 'email' in their name",
        "Do you have a tool called 'gmail_search_emails'?",
        "Can you search my Gmail inbox?",
        "What MCP servers are currently loaded?",
    ]

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n{'=' * 80}")
        print(f"Test {i}/{len(test_prompts)}: {prompt}")
        print("=" * 80)

        cmd = [
            'claude',
            '--print',
            '--mcp-config', config_path,
            '--output-format', 'text',
            prompt
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            print(f"Exit code: {result.returncode}")
            print(f"\nResponse:")
            print("-" * 80)
            print(result.stdout)
            print("-" * 80)

            if result.stderr:
                print(f"\nStderr:")
                print(result.stderr)

        except subprocess.TimeoutExpired:
            print("TIMEOUT")
        except Exception as e:
            print(f"ERROR: {e}")

    os.unlink(config_path)


def test_gmail_with_debug():
    """Test with debug mode to see MCP server initialization."""

    print("\n" + "=" * 80)
    print("TEST: Gmail MCP with Debug Mode")
    print("=" * 80)

    config = {
        "mcpServers": {
            "gmail": {
                "command": "npx",
                "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
                "env": {
                    "GMAIL_OAUTH_PATH": "/Users/james.cahoon/.gmail-mcp/gcp-oauth.keys.json",
                    "GMAIL_CREDENTIALS_PATH": "/Users/james.cahoon/.gmail-mcp/credentials.json"
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, indent=2)
        config_path = f.name

    cmd = [
        'claude',
        '--print',
        '--debug',  # Enable all debug
        '--mcp-config', config_path,
        '--output-format', 'text',
        'Do you have gmail tools available? List them.'
    ]

    print(f"Running with full debug mode...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=os.environ.copy()
        )

        print(f"Exit code: {result.returncode}")
        print(f"\nSTDOUT:")
        print("-" * 80)
        print(result.stdout)
        print("-" * 80)

        if result.stderr:
            print(f"\nSTDERR (Debug output):")
            print("-" * 80)
            print(result.stderr)
            print("-" * 80)

    except subprocess.TimeoutExpired:
        print("TIMEOUT")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        os.unlink(config_path)


def test_json_output_format():
    """Test with JSON output to see tool calls."""

    print("\n" + "=" * 80)
    print("TEST: JSON Output Format")
    print("=" * 80)

    config = {
        "mcpServers": {
            "gmail": {
                "command": "npx",
                "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
                "env": {
                    "GMAIL_OAUTH_PATH": "/Users/james.cahoon/.gmail-mcp/gcp-oauth.keys.json",
                    "GMAIL_CREDENTIALS_PATH": "/Users/james.cahoon/.gmail-mcp/credentials.json"
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, indent=2)
        config_path = f.name

    cmd = [
        'claude',
        '--print',
        '--mcp-config', config_path,
        '--output-format', 'json',  # JSON output
        'List all available tools'
    ]

    print("Using JSON output format to inspect tool list...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        print(f"Exit code: {result.returncode}")

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                print(f"\nJSON Response structure:")
                print(json.dumps(data, indent=2)[:2000])  # First 2000 chars
            except json.JSONDecodeError:
                print("Failed to parse JSON")
                print(result.stdout[:1000])

        if result.stderr:
            print(f"\nStderr:")
            print(result.stderr[:1000])

    except subprocess.TimeoutExpired:
        print("TIMEOUT")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        os.unlink(config_path)


def test_actual_gmail_operation():
    """Test if we can actually execute a Gmail operation."""

    print("\n" + "=" * 80)
    print("TEST: Actual Gmail Operation (Count Unread Emails)")
    print("=" * 80)

    config = {
        "mcpServers": {
            "gmail": {
                "command": "npx",
                "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
                "env": {
                    "GMAIL_OAUTH_PATH": "/Users/james.cahoon/.gmail-mcp/gcp-oauth.keys.json",
                    "GMAIL_CREDENTIALS_PATH": "/Users/james.cahoon/.gmail-mcp/credentials.json"
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, indent=2)
        config_path = f.name

    # This should actually call the Gmail API if tools are loaded
    cmd = [
        'claude',
        '--print',
        '--mcp-config', config_path,
        '--output-format', 'text',
        'How many unread emails do I have in my inbox?'
    ]

    print("Attempting to count unread emails...")
    print("(This will only work if MCP server loads and tools are available)")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # Longer timeout for actual API call
        )

        print(f"\nExit code: {result.returncode}")
        print(f"\nResponse:")
        print("-" * 80)
        print(result.stdout)
        print("-" * 80)

        if result.stderr:
            print(f"\nStderr:")
            print(result.stderr)

        # Check if response contains actual numbers or error messages
        if any(word in result.stdout.lower() for word in ['unread', 'email', 'inbox', 'message']):
            print("\n✓ Response mentions email-related terms")
        else:
            print("\n✗ Response doesn't seem email-related")

    except subprocess.TimeoutExpired:
        print("TIMEOUT (API call may have hung)")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        os.unlink(config_path)


def main():
    print("\n" + "=" * 80)
    print("GMAIL MCP TOOLS AVAILABILITY TEST")
    print("Testing if Gmail tools load via Claude CLI + MCP config")
    print("=" * 80 + "\n")

    test_gmail_tools_available()
    test_gmail_with_debug()
    test_json_output_format()
    test_actual_gmail_operation()

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("\nKey Questions:")
    print("1. Do Gmail tools appear in the tool list?")
    print("2. Can Claude see the MCP server is loaded?")
    print("3. Can we actually execute Gmail operations?")
    print("4. Do env vars pass through correctly to the MCP server?")


if __name__ == "__main__":
    main()
