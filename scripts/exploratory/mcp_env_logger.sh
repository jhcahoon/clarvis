#!/bin/bash
# MCP Environment Variable Logger
# This wrapper logs all environment variables before launching the real MCP server
# Usage: Replace "npx" command with this script in MCP config

LOG_FILE="/tmp/mcp_env_debug_$(date +%Y%m%d_%H%M%S).log"

echo "=== MCP Environment Logger ===" >> "$LOG_FILE"
echo "Timestamp: $(date)" >> "$LOG_FILE"
echo "Working Directory: $(pwd)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== All Environment Variables ===" >> "$LOG_FILE"
env | sort >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== Gmail-Specific Variables ===" >> "$LOG_FILE"
echo "GMAIL_OAUTH_PATH=${GMAIL_OAUTH_PATH:-NOT SET}" >> "$LOG_FILE"
echo "GMAIL_CREDENTIALS_PATH=${GMAIL_CREDENTIALS_PATH:-NOT SET}" >> "$LOG_FILE"
echo "GMAIL_TOKEN_PATH=${GMAIL_TOKEN_PATH:-NOT SET}" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== Arguments Received ===" >> "$LOG_FILE"
echo "Args: $@" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "Log written to: $LOG_FILE" >&2

# Now launch the actual MCP server with all arguments
exec npx "$@"
