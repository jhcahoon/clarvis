#!/usr/bin/env python3
"""
DEMONSTRATION: Using Claude CLI directly to bypass Python SDK

This script shows the practical application of our findings.
"""

import subprocess
import json
import tempfile
import os
from pathlib import Path


def get_mcp_config_path() -> str:
    """Get the MCP config path, preferring local over example."""
    config_dir = Path(__file__).parent.parent.parent / "configs"
    local_config = config_dir / "mcp_servers.local.json"
    example_config = config_dir / "mcp_servers.json.example"

    if local_config.exists():
        return str(local_config)
    elif example_config.exists():
        return str(example_config)
    else:
        return str(config_dir / "mcp_servers.json")


def call_claude_cli(prompt: str, mcp_config_path: str = None, output_format: str = "text") -> dict:
    """
    Call Claude CLI directly with MCP server configuration.

    Args:
        prompt: The prompt to send to Claude
        mcp_config_path: Path to MCP servers JSON config file
        output_format: "text", "json", or "stream-json"

    Returns:
        dict with 'success', 'stdout', 'stderr', 'exit_code'
    """
    cmd = ['claude', '--print']

    if mcp_config_path:
        cmd.extend(['--mcp-config', mcp_config_path])

    cmd.extend(['--output-format', output_format, prompt])

    print(f"Executing: {' '.join(cmd[:6])}...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exit_code': result.returncode
        }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'timeout',
            'stdout': '',
            'stderr': 'Command timed out after 60 seconds'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'stdout': '',
            'stderr': str(e)
        }


def demo_1_simple_call():
    """Demo 1: Simple call without MCP servers."""
    print("=" * 80)
    print("DEMO 1: Simple Claude CLI call (no MCP)")
    print("=" * 80)

    result = call_claude_cli("What is 2+2? Just answer with the number.")

    print(f"Success: {result['success']}")
    print(f"Response: {result['stdout']}")


def demo_2_with_gmail_mcp():
    """Demo 2: Call with Gmail MCP server."""
    print("\n" + "=" * 80)
    print("DEMO 2: Claude CLI with Gmail MCP server")
    print("=" * 80)

    # Use existing config
    config_path = get_mcp_config_path()

    result = call_claude_cli(
        "List the first 5 Gmail tools you have. Just list their names, one per line.",
        mcp_config_path=config_path
    )

    print(f"Success: {result['success']}")
    print(f"Response:\n{result['stdout']}")


def demo_3_json_output():
    """Demo 3: Using JSON output format."""
    print("\n" + "=" * 80)
    print("DEMO 3: JSON output format for programmatic parsing")
    print("=" * 80)

    config_path = get_mcp_config_path()

    result = call_claude_cli(
        "How many gmail tools do you have? Answer with just the number.",
        mcp_config_path=config_path,
        output_format="json"
    )

    if result['success']:
        try:
            data = json.loads(result['stdout'])
            print("JSON structure:")
            print(f"  type: {data.get('type')}")
            print(f"  is_error: {data.get('is_error')}")
            print(f"  duration_ms: {data.get('duration_ms')}")
            print(f"  num_turns: {data.get('num_turns')}")
            print(f"\nResult text:")
            print(f"  {data.get('result')}")
        except json.JSONDecodeError:
            print("Failed to parse JSON")
            print(result['stdout'])
    else:
        print(f"Failed: {result.get('stderr')}")


def demo_4_dynamic_config():
    """Demo 4: Create MCP config dynamically."""
    print("\n" + "=" * 80)
    print("DEMO 4: Dynamic MCP config generation")
    print("=" * 80)

    # Build config programmatically
    config = {
        "mcpServers": {
            "gmail": {
                "command": "npx",
                "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
                "env": {
                    "GMAIL_OAUTH_PATH": os.path.expanduser("~/.gmail-mcp/gcp-oauth.keys.json"),
                    "GMAIL_CREDENTIALS_PATH": os.path.expanduser("~/.gmail-mcp/credentials.json")
                }
            }
        }
    }

    print("Generated config:")
    print(json.dumps(config, indent=2))

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_config = f.name

    print(f"\nTemp config file: {temp_config}")

    result = call_claude_cli(
        "Do you have access to Gmail? Answer yes or no.",
        mcp_config_path=temp_config
    )

    print(f"\nResponse: {result['stdout']}")

    # Cleanup
    os.unlink(temp_config)
    print(f"Cleaned up temp file")


def demo_5_env_vars_via_subprocess():
    """Demo 5: Pass env vars via subprocess instead of config."""
    print("\n" + "=" * 80)
    print("DEMO 5: Environment variables via subprocess.run")
    print("=" * 80)

    # Config WITHOUT env vars
    config = {
        "mcpServers": {
            "gmail": {
                "command": "npx",
                "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"]
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_config = f.name

    # Set env vars via subprocess
    custom_env = os.environ.copy()
    custom_env['GMAIL_OAUTH_PATH'] = os.path.expanduser('~/.gmail-mcp/gcp-oauth.keys.json')
    custom_env['GMAIL_CREDENTIALS_PATH'] = os.path.expanduser('~/.gmail-mcp/credentials.json')

    print("Config (no env vars):")
    print(json.dumps(config, indent=2))
    print(f"\nEnv vars set via subprocess:")
    print(f"  GMAIL_OAUTH_PATH={custom_env['GMAIL_OAUTH_PATH']}")
    print(f"  GMAIL_CREDENTIALS_PATH={custom_env['GMAIL_CREDENTIALS_PATH']}")

    cmd = [
        'claude',
        '--print',
        '--mcp-config', temp_config,
        '--output-format', 'text',
        'Do you have Gmail tools? Yes or no.'
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=custom_env,
        timeout=60
    )

    print(f"\nResponse: {result.stdout}")

    os.unlink(temp_config)


def demo_6_real_gmail_query():
    """Demo 6: Actual Gmail query (requires auth)."""
    print("\n" + "=" * 80)
    print("DEMO 6: Real Gmail query (will prompt for auth if needed)")
    print("=" * 80)

    config_path = get_mcp_config_path()

    print("Asking Claude to search Gmail...")
    print("(This may prompt for OAuth authorization)")

    result = call_claude_cli(
        "Search my Gmail for emails with the word 'test' in the subject. Just tell me how many you found.",
        mcp_config_path=config_path
    )

    print(f"\nSuccess: {result['success']}")
    print(f"Response:\n{result['stdout']}")

    if result['stderr']:
        print(f"\nStderr:\n{result['stderr']}")


def main():
    print("\n" + "=" * 80)
    print("CLAUDE CLI DIRECT LAUNCH - PRACTICAL DEMONSTRATIONS")
    print("=" * 80)
    print("\nThese demos show real-world usage of Claude CLI with MCP servers")
    print("bypassing the Python SDK entirely.\n")

    # Run demos
    demo_1_simple_call()
    demo_2_with_gmail_mcp()
    demo_3_json_output()
    demo_4_dynamic_config()
    demo_5_env_vars_via_subprocess()

    print("\n" + "=" * 80)
    print("Note: Skipping Demo 6 (real Gmail query) to avoid OAuth prompts")
    print("Uncomment demo_6_real_gmail_query() to test actual Gmail access")
    print("=" * 80)

    # Uncomment to test real Gmail access:
    # demo_6_real_gmail_query()

    print("\n" + "=" * 80)
    print("DEMONSTRATIONS COMPLETE")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("1. Claude CLI can be called directly via subprocess.run()")
    print("2. MCP servers load successfully with --mcp-config")
    print("3. Environment variables can be passed via config or subprocess env")
    print("4. Both text and JSON output formats work")
    print("5. No Python SDK dependencies needed!")


if __name__ == "__main__":
    main()
