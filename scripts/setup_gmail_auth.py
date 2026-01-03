#!/usr/bin/env python3
"""
Gmail OAuth Setup Helper

This script guides users through setting up Gmail OAuth credentials
for the MCP server.
"""

import os
import json
from pathlib import Path
import webbrowser
import sys


def setup_gmail_credentials() -> bool:
    """
    Interactive setup for Gmail OAuth credentials.

    Returns:
        True if setup was successful, False otherwise
    """
    print("=== Gmail Agent OAuth Setup ===\n")

    # Create directory
    gmail_mcp_dir = Path.home() / ".gmail-mcp"
    gmail_mcp_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {gmail_mcp_dir}\n")

    # Check if credentials already exist
    cred_path = gmail_mcp_dir / "gcp-oauth.keys.json"
    if cred_path.exists():
        overwrite = input("Credentials already exist. Overwrite? (y/n): ")
        if overwrite.lower() != 'y':
            print("Setup cancelled.")
            return False

    print("Step 1: Create Google Cloud Project")
    print("  1. Go to: https://console.cloud.google.com")
    print("  2. Create new project 'Clarvis Gmail Agent' (or use existing)")
    print("  3. Enable Gmail API for the project")

    input("\nPress Enter when done...")

    print("\nStep 2: Create OAuth Credentials")
    print("  1. Go to: APIs & Services > Credentials")
    print("  2. Click 'Create Credentials' > 'OAuth 2.0 Client ID'")
    print("  3. Application type: Desktop App")
    print("  4. Name: 'Gmail Agent' (or your choice)")
    print("  5. Click 'Create'")
    print("  6. Click 'Download JSON' button")

    open_console = input("\nOpen Google Cloud Console? (y/n): ")
    if open_console.lower() == 'y':
        webbrowser.open("https://console.cloud.google.com/apis/credentials")

    input("\nPress Enter when you've downloaded credentials.json...")

    print("\nStep 3: Place Credentials")
    print("  Note: The file will be saved as 'gcp-oauth.keys.json' (required by MCP server)")

    # Ask for the path to the downloaded credentials
    while True:
        source_path_str = input(f"\nEnter path to downloaded credentials.json (or 'q' to quit): ").strip()

        if source_path_str.lower() == 'q':
            print("Setup cancelled.")
            return False

        # Remove quotes if present
        source_path_str = source_path_str.strip('"').strip("'")

        # Expand user home directory
        source_path = Path(source_path_str).expanduser()

        if source_path.exists():
            try:
                # Validate it's valid JSON
                with open(source_path, 'r') as f:
                    cred_data = json.load(f)

                # Check if it has the expected structure
                if "installed" not in cred_data and "web" not in cred_data:
                    print("Warning: This doesn't look like a valid OAuth credentials file.")
                    continue_anyway = input("Continue anyway? (y/n): ")
                    if continue_anyway.lower() != 'y':
                        continue

                # Copy to target location
                import shutil
                shutil.copy(source_path, cred_path)

                # Set restrictive permissions
                os.chmod(cred_path, 0o600)

                print(f"\n✓ Credentials copied to {cred_path}")
                print(f"✓ File permissions set to 600 (owner read/write only)")
                break

            except json.JSONDecodeError:
                print("Error: File is not valid JSON. Please check the file and try again.")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print(f"File not found: {source_path}")
            print("Please check the path and try again.")

    # Create .gitignore to prevent accidental commits
    gitignore_path = gmail_mcp_dir / ".gitignore"
    with open(gitignore_path, 'w') as f:
        f.write("# Prevent accidentally committing OAuth credentials\n")
        f.write("credentials.json\n")
        f.write("token.json\n")
    print(f"✓ Created .gitignore at {gitignore_path}")

    print("\n=== Setup Complete! ===")
    print(f"Credentials stored at: {cred_path}")
    print("\nNext steps:")
    print("  1. Install MCP server:")
    print("     npx -y @smithery/cli install @gongrzhe/server-gmail-autoauth-mcp --client claude")
    print("\n  2. Test the agent:")
    print("     python -m agents.gmail_agent")
    print("\n  3. On first run, you'll be prompted to authenticate with Google")
    print("     A browser window will open for OAuth consent")

    print("\nNote: The token.json file will be created automatically after first authentication.")

    return True


def main() -> int:
    """Main entry point."""
    try:
        success = setup_gmail_credentials()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        return 1
    except Exception as e:
        print(f"\nError during setup: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
