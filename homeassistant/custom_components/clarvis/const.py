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
GMAIL_QUERY_ENDPOINT = "/api/v1/gmail/query"

# Intent detection keywords for email-related queries
EMAIL_KEYWORDS = [
    "email",
    "emails",
    "inbox",
    "gmail",
    "unread",
    "messages",
    "mail",
    "mailbox",
    "message",
]
