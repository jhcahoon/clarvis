#!/bin/bash
# Wrapper to log environment variables the MCP server receives

echo "[MCP WRAPPER] Environment variables:" >&2
echo "GMAIL_OAUTH_PATH=$GMAIL_OAUTH_PATH" >&2
echo "GMAIL_CREDENTIALS_PATH=$GMAIL_CREDENTIALS_PATH" >&2
echo "[MCP WRAPPER] Launching MCP server..." >&2

# Launch the actual MCP server
exec npx -y @gongrzhe/server-gmail-autoauth-mcp "$@"
