#!/usr/bin/env python3
"""
Focused test on CLI direct launch - investigating the timeout issue.
"""

import subprocess
import json
import os
import tempfile
import time
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

def test_mcp_config_variants():
    """Test different ways to pass MCP config to Claude CLI."""

    # Test 1: Config with tilde expansion (original)
    print("=" * 80)
    print("TEST 1: Config with tilde paths")
    print("=" * 80)

    config_tilde = {
        "mcpServers": {
            "gmail": {
                "command": "npx",
                "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
                "env": {
                    "GMAIL_OAUTH_PATH": "~/.gmail-mcp/gcp-oauth.keys.json",
                    "GMAIL_CREDENTIALS_PATH": "~/.gmail-mcp/credentials.json"
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_tilde, f, indent=2)
        config_path_tilde = f.name

    cmd = [
        'claude',
        '--print',
        '--mcp-config', config_path_tilde,
        '--output-format', 'text',
        'What tools are available?'
    ]

    print(f"Config: {json.dumps(config_tilde, indent=2)}")
    print(f"\nRunning command with 60s timeout...")

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        elapsed = time.time() - start
        print(f"✓ Completed in {elapsed:.2f}s")
        print(f"Exit code: {result.returncode}")
        print(f"Output length: {len(result.stdout)} chars")
        if result.stdout:
            print(f"First 500 chars:\n{result.stdout[:500]}")
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"✗ TIMEOUT after {elapsed:.2f}s")
    finally:
        os.unlink(config_path_tilde)

    # Test 2: Config with absolute paths
    print("\n" + "=" * 80)
    print("TEST 2: Config with absolute paths")
    print("=" * 80)

    config_absolute = {
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
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_absolute, f, indent=2)
        config_path_absolute = f.name

    cmd = [
        'claude',
        '--print',
        '--mcp-config', config_path_absolute,
        '--output-format', 'text',
        'What tools are available?'
    ]

    print(f"Config: {json.dumps(config_absolute, indent=2)}")
    print(f"\nRunning command with 60s timeout...")

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        elapsed = time.time() - start
        print(f"✓ Completed in {elapsed:.2f}s")
        print(f"Exit code: {result.returncode}")
        print(f"Output length: {len(result.stdout)} chars")
        if result.stdout:
            print(f"First 500 chars:\n{result.stdout[:500]}")
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"✗ TIMEOUT after {elapsed:.2f}s")
    finally:
        os.unlink(config_path_absolute)

    # Test 3: Using existing config file
    print("\n" + "=" * 80)
    print("TEST 3: Using existing config file")
    print("=" * 80)

    existing_config = get_mcp_config_path()

    # First check what's in it
    with open(existing_config, 'r') as f:
        existing_content = json.load(f)

    print(f"Existing config: {json.dumps(existing_content, indent=2)}")

    cmd = [
        'claude',
        '--print',
        '--mcp-config', existing_config,
        '--output-format', 'text',
        'List your tools'
    ]

    print(f"\nRunning command with 60s timeout...")

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        elapsed = time.time() - start
        print(f"✓ Completed in {elapsed:.2f}s")
        print(f"Exit code: {result.returncode}")
        print(f"Output length: {len(result.stdout)} chars")
        if result.stdout:
            print(f"First 500 chars:\n{result.stdout[:500]}")
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"✗ TIMEOUT after {elapsed:.2f}s")

    # Test 4: Debug mode to see what's happening
    print("\n" + "=" * 80)
    print("TEST 4: With debug mode enabled")
    print("=" * 80)

    cmd = [
        'claude',
        '--print',
        '--debug', 'mcp',
        '--mcp-config', existing_config,
        '--output-format', 'text',
        'What can you do?'
    ]

    print(f"Running with MCP debug enabled...")

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        elapsed = time.time() - start
        print(f"✓ Completed in {elapsed:.2f}s")
        print(f"Exit code: {result.returncode}")
        print(f"\nSTDOUT ({len(result.stdout)} chars):\n{result.stdout}")
        if result.stderr:
            print(f"\nSTDERR ({len(result.stderr)} chars):\n{result.stderr}")
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"✗ TIMEOUT after {elapsed:.2f}s")


def test_env_var_methods():
    """Test different methods of passing environment variables."""

    print("\n" + "=" * 80)
    print("TEST 5: Environment variables - subprocess.run env parameter")
    print("=" * 80)

    config = {
        "mcpServers": {
            "gmail": {
                "command": "npx",
                "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"]
                # NO env vars in config
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, indent=2)
        config_path = f.name

    # Set env vars via subprocess env parameter
    custom_env = os.environ.copy()
    custom_env['GMAIL_OAUTH_PATH'] = str(Path.home() / ".gmail-mcp" / "gcp-oauth.keys.json")
    custom_env['GMAIL_CREDENTIALS_PATH'] = str(Path.home() / ".gmail-mcp" / "credentials.json")

    print("Env vars set via subprocess.run env parameter:")
    print(f"  GMAIL_OAUTH_PATH={custom_env['GMAIL_OAUTH_PATH']}")
    print(f"  GMAIL_CREDENTIALS_PATH={custom_env['GMAIL_CREDENTIALS_PATH']}")
    print(f"\nConfig (no env vars): {json.dumps(config, indent=2)}")

    cmd = [
        'claude',
        '--print',
        '--mcp-config', config_path,
        '--output-format', 'text',
        'What tools do you have?'
    ]

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            env=custom_env  # Pass custom env here
        )
        elapsed = time.time() - start
        print(f"\n✓ Completed in {elapsed:.2f}s")
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout[:500]}")
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"✗ TIMEOUT after {elapsed:.2f}s")
    finally:
        os.unlink(config_path)


def main():
    print("\n" + "=" * 80)
    print("CLAUDE CLI DIRECT LAUNCH - DETAILED INVESTIGATION")
    print("=" * 80 + "\n")

    test_mcp_config_variants()
    test_env_var_methods()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nKey Observations:")
    print("1. Tilde paths (~/) vs absolute paths - which works?")
    print("2. Does the CLI timeout on certain config files?")
    print("3. Can env vars be passed via subprocess.run env param?")
    print("4. What do debug logs reveal?")


if __name__ == "__main__":
    main()
