"""Native tools for Ski Agent using Claude Agent SDK."""

import logging
from typing import Optional

import httpx
from claude_agent_sdk import create_sdk_mcp_server, tool

logger = logging.getLogger(__name__)

# Default URL for Mt Hood Meadows conditions
DEFAULT_CONDITIONS_URL = "https://cloudserv.skihood.com/"

# Module-level default URL. Use set_conditions_url() to override for testing.
# Note: This is module-level state. For production use, pass URL via tool parameter.
_conditions_url: str = DEFAULT_CONDITIONS_URL


def set_conditions_url(url: str) -> None:
    """Set the default conditions URL (primarily for testing).

    Note: Prefer passing the URL directly to fetch_ski_conditions() when possible.

    Args:
        url: The URL to use as the default for fetching conditions.
    """
    global _conditions_url
    _conditions_url = url


def get_conditions_url() -> str:
    """Get the current default conditions URL."""
    return _conditions_url


# Implementation functions (testable without SDK)


async def fetch_ski_conditions_impl(url: Optional[str] = None) -> str:
    """Fetch ski conditions from the specified URL.

    Args:
        url: URL to fetch conditions from. Defaults to cloudserv.skihood.com.

    Returns:
        Raw HTML/text content from the conditions page.
    """
    target_url = url or get_conditions_url()
    logger.info(f"Fetching ski conditions from {target_url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                target_url,
                timeout=15.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Clarvis-SkiAgent/1.0 (Home Assistant Integration)"
                },
            )
            response.raise_for_status()
            logger.info(f"Successfully fetched conditions ({len(response.text)} bytes)")
            return response.text

    except httpx.TimeoutException:
        logger.error(f"Timeout fetching conditions from {target_url}")
        return "Error: Request timed out. The ski conditions server may be slow or unavailable."

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching conditions: {e.response.status_code}")
        return f"Error: Server returned status {e.response.status_code}. Unable to fetch conditions."

    except httpx.RequestError as e:
        logger.error(f"Request error fetching conditions: {e}")
        return "Error: Unable to connect to ski conditions server. Please try again later."

    except Exception as e:
        logger.error(f"Unexpected error fetching conditions: {e}", exc_info=True)
        return "Error: An unexpected error occurred while fetching conditions. Please try again later."


# SDK Tool definitions


@tool(
    name="fetch_ski_conditions",
    description="Fetch current ski conditions from Mt Hood Meadows. Returns raw HTML/text content with snow depths, lift status, weather, and other conditions data.",
    input_schema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Optional URL to fetch conditions from. Defaults to cloudserv.skihood.com.",
            },
        },
        "required": [],
    },
)
async def fetch_ski_conditions(url: Optional[str] = None) -> str:
    """Fetch ski conditions from Mt Hood Meadows."""
    return await fetch_ski_conditions_impl(url)


# Create the SDK MCP server with native tools
ski_tools_server = create_sdk_mcp_server(
    name="ski_tools",
    version="1.0.0",
    tools=[fetch_ski_conditions],
)
