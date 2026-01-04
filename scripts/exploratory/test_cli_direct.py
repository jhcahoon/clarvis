#!/usr/bin/env python3
"""
Test bypassing Python SDK to use Claude CLI directly with MCP servers.

This test investigates:
1. Can we launch claude CLI directly with MCP config?
2. Do environment variables pass through correctly?
3. What's the difference vs Python SDK approach?
"""

import subprocess
import json
import os
from pathlib import Path
import tempfile


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
        # Fallback for backwards compatibility
        return str(config_dir / "mcp_servers.json")

def test_1_find_claude_executable():
    """Test 1: Verify claude CLI is available."""
    print("=" * 80)
    print("TEST 1: Find Claude CLI Executable")
    print("=" * 80)

    result = subprocess.run(['which', 'claude'], capture_output=True, text=True)
    print(f"which claude: {result.stdout.strip()}")
    print(f"Exit code: {result.returncode}")

    if result.returncode == 0:
        version_result = subprocess.run(['claude', '--version'], capture_output=True, text=True)
        print(f"Version: {version_result.stdout.strip()}")
        return result.stdout.strip()
    else:
        print("ERROR: claude CLI not found!")
        return None


def test_2_check_mcp_options():
    """Test 2: Check claude CLI MCP-related options."""
    print("\n" + "=" * 80)
    print("TEST 2: Check MCP Options in CLI")
    print("=" * 80)

    result = subprocess.run(['claude', '--help'], capture_output=True, text=True)

    # Extract MCP-related options
    for line in result.stdout.split('\n'):
        if 'mcp' in line.lower():
            print(line)


def test_3_launch_cli_with_mcp_config():
    """Test 3: Launch claude CLI with MCP config file."""
    print("\n" + "=" * 80)
    print("TEST 3: Launch Claude CLI with MCP Config")
    print("=" * 80)

    # Use existing MCP config (local or example)
    mcp_config_path = get_mcp_config_path()

    print(f"Using MCP config: {mcp_config_path}")

    # Create a simple test prompt
    test_prompt = "List available MCP tools and tell me what you can do with Gmail"

    # Try launching claude with MCP config
    cmd = [
        'claude',
        '--print',  # Non-interactive mode
        '--mcp-config', mcp_config_path,
        '--output-format', 'text',
        test_prompt
    ]

    print(f"\nCommand: {' '.join(cmd)}")
    print("\nAttempting to run...")
    print("-" * 80)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=os.environ.copy()
        )

        print(f"Exit code: {result.returncode}")
        print(f"\nSTDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"\nSTDERR:\n{result.stderr}")

        return result
    except subprocess.TimeoutExpired:
        print("ERROR: Command timed out after 30 seconds")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def test_4_env_vars_with_mcp_config():
    """Test 4: Test if env vars from MCP config are passed through."""
    print("\n" + "=" * 80)
    print("TEST 4: Test Environment Variable Pass-through")
    print("=" * 80)

    # Create a test MCP config with explicit env vars
    test_config = {
        "mcpServers": {
            "gmail": {
                "command": "npx",
                "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
                "env": {
                    "GMAIL_OAUTH_PATH": str(Path.home() / ".gmail-mcp" / "gcp-oauth.keys.json"),
                    "GMAIL_CREDENTIALS_PATH": str(Path.home() / ".gmail-mcp" / "credentials.json"),
                    "DEBUG_MCP": "1",
                    "TEST_VAR": "test_value_from_config"
                }
            }
        }
    }

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_config, f, indent=2)
        temp_config_path = f.name

    print(f"Created temp config: {temp_config_path}")
    print(f"Config contents:\n{json.dumps(test_config, indent=2)}")

    test_prompt = "What MCP tools are available? Can you check environment variables?"

    cmd = [
        'claude',
        '--print',
        '--mcp-config', temp_config_path,
        '--output-format', 'text',
        test_prompt
    ]

    print(f"\nCommand: {' '.join(cmd)}")
    print("\nRunning with env vars from config...")
    print("-" * 80)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=os.environ.copy()
        )

        print(f"Exit code: {result.returncode}")
        print(f"\nSTDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"\nSTDERR:\n{result.stderr}")

        # Cleanup
        os.unlink(temp_config_path)
        return result
    except subprocess.TimeoutExpired:
        print("ERROR: Command timed out")
        os.unlink(temp_config_path)
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        os.unlink(temp_config_path)
        return None


def test_5_compare_with_inline_mcp_config():
    """Test 5: Try passing MCP config as inline JSON string."""
    print("\n" + "=" * 80)
    print("TEST 5: Test Inline MCP Config (JSON String)")
    print("=" * 80)

    # Try inline config (if supported)
    inline_config = json.dumps({
        "mcpServers": {
            "gmail": {
                "command": "npx",
                "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
                "env": {
                    "GMAIL_OAUTH_PATH": str(Path.home() / ".gmail-mcp" / "gcp-oauth.keys.json"),
                    "GMAIL_CREDENTIALS_PATH": str(Path.home() / ".gmail-mcp" / "credentials.json")
                }
            }
        }
    })

    print(f"Inline config: {inline_config}")

    cmd = [
        'claude',
        '--print',
        '--mcp-config', inline_config,
        '--output-format', 'text',
        'What tools do you have available?'
    ]

    print(f"\nCommand: {' '.join(cmd[:4])} <inline-json> ...")
    print("\nRunning...")
    print("-" * 80)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=os.environ.copy()
        )

        print(f"Exit code: {result.returncode}")
        print(f"\nSTDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"\nSTDERR:\n{result.stderr}")

        return result
    except subprocess.TimeoutExpired:
        print("ERROR: Command timed out")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def test_6_subprocess_env_override():
    """Test 6: Test if we can override env vars via subprocess.run."""
    print("\n" + "=" * 80)
    print("TEST 6: Test Subprocess Environment Override")
    print("=" * 80)

    mcp_config_path = get_mcp_config_path()

    # Create custom environment with additional vars
    custom_env = os.environ.copy()
    custom_env['GMAIL_OAUTH_PATH'] = str(Path.home() / ".gmail-mcp" / "gcp-oauth.keys.json")
    custom_env['GMAIL_CREDENTIALS_PATH'] = str(Path.home() / ".gmail-mcp" / "credentials.json")
    custom_env['DEBUG_MCP'] = '1'
    custom_env['CUSTOM_TEST_VAR'] = 'from_subprocess_env'

    print("Custom environment variables:")
    for key in ['GMAIL_OAUTH_PATH', 'GMAIL_CREDENTIALS_PATH', 'DEBUG_MCP', 'CUSTOM_TEST_VAR']:
        print(f"  {key} = {custom_env.get(key)}")

    cmd = [
        'claude',
        '--print',
        '--mcp-config', mcp_config_path,
        '--output-format', 'text',
        'What MCP servers are configured?'
    ]

    print(f"\nCommand: {' '.join(cmd)}")
    print("\nRunning with custom env...")
    print("-" * 80)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=custom_env
        )

        print(f"Exit code: {result.returncode}")
        print(f"\nSTDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"\nSTDERR:\n{result.stderr}")

        return result
    except subprocess.TimeoutExpired:
        print("ERROR: Command timed out")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("CLAUDE CLI DIRECT LAUNCH INVESTIGATION")
    print("Testing if we can bypass Python SDK for MCP server launch")
    print("=" * 80 + "\n")

    # Run tests
    claude_path = test_1_find_claude_executable()

    if not claude_path:
        print("\nERROR: Cannot proceed without claude CLI")
        return

    test_2_check_mcp_options()
    test_3_launch_cli_with_mcp_config()
    test_4_env_vars_with_mcp_config()
    test_5_compare_with_inline_mcp_config()
    test_6_subprocess_env_override()

    print("\n" + "=" * 80)
    print("INVESTIGATION COMPLETE")
    print("=" * 80)
    print("\nKey Findings:")
    print("1. Claude CLI path:", claude_path)
    print("2. MCP config option: --mcp-config (supports files and potentially JSON strings)")
    print("3. Environment variables: Can be set in MCP config or via subprocess env")
    print("\nNext Steps:")
    print("- Review output above to see if MCP servers loaded correctly")
    print("- Check if env vars from config.env are passed to MCP servers")
    print("- Compare with Python SDK behavior")


if __name__ == "__main__":
    main()
