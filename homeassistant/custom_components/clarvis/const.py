"""Constants for the Clarvis AI Assistant integration."""

DOMAIN = "clarvis"

# Configuration keys
CONF_API_HOST = "api_host"
CONF_API_PORT = "api_port"

# Default values
DEFAULT_API_HOST = "10.0.0.23"
DEFAULT_API_PORT = 8000
DEFAULT_TIMEOUT = 120

# API endpoints
HEALTH_ENDPOINT = "/health"
ORCHESTRATOR_QUERY_ENDPOINT = "/api/v1/query"

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
