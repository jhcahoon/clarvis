"""Constants for the Clarvis AI Assistant integration."""

import os

DOMAIN = "clarvis"

# Configuration keys
CONF_API_HOST = "api_host"
CONF_API_PORT = "api_port"

# Default values - configurable via environment variables
# For local development, use localhost. For production, set CLARVIS_API_HOST.
DEFAULT_API_HOST = os.environ.get("CLARVIS_API_HOST", "localhost")
DEFAULT_API_PORT = int(os.environ.get("CLARVIS_API_PORT", "8000"))
DEFAULT_TIMEOUT = 120

# API endpoints
HEALTH_ENDPOINT = "/health"
ORCHESTRATOR_QUERY_ENDPOINT = "/api/v1/query"
ORCHESTRATOR_STREAM_ENDPOINT = "/api/v1/query/stream"

# Home Assistant command keywords for smart fallback detection
# If orchestrator can't handle a query AND it matches these keywords,
# fall back to HA's default agent for device control
HA_COMMAND_KEYWORDS = [
    "turn on",
    "turn off",
    "switch on",
    "switch off",
    "dim",
    "brighten",
    "set temperature",
    "set thermostat",
    "lock",
    "unlock",
    "open",
    "close",
    "arm",
    "disarm",
    "play",
    "pause",
    "stop",
    "volume",
    "mute",
    "unmute",
]
