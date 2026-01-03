"""Custom tools for Gmail Agent using Claude Agent SDK."""

from claude_agent_sdk import tool, create_sdk_mcp_server
from datetime import datetime, timedelta


@tool(
    name="check_inbox",
    description="Provides guidance for checking inbox emails - returns suggested Gmail search query",
    input_schema={
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 10
            },
            "unread_only": {
                "type": "boolean",
                "description": "If true, only show unread emails; if false, show all emails",
                "default": True
            }
        },
        "required": []
    }
)
async def check_inbox(max_results: int = 10, unread_only: bool = True) -> str:
    """
    Quick inbox check - provides guidance for searching recent emails.

    This is a helper tool that suggests the appropriate Gmail search query
    for checking the inbox.

    Args:
        max_results: Maximum number of emails to return (default: 10)
        unread_only: Only return unread emails (default: True)

    Returns:
        Suggested search query and parameters
    """
    query = "is:unread in:inbox" if unread_only else "in:inbox"

    return f"""To check inbox:
- Use the gmail_search_emails MCP tool
- Query: "{query}"
- Max results: {max_results}
- This will show {"unread" if unread_only else "all"} emails in the inbox"""


@tool(
    name="summarize_email_thread",
    description="Get guidance for summarizing a full email thread by thread ID",
    input_schema={
        "type": "object",
        "properties": {
            "thread_id": {
                "type": "string",
                "description": "Gmail thread ID to summarize"
            }
        },
        "required": ["thread_id"]
    }
)
async def summarize_email_thread(thread_id: str) -> str:
    """
    Get guidance for summarizing a full email thread.

    This helper tool provides instructions for retrieving and summarizing
    an email thread.

    Args:
        thread_id: Gmail thread ID to summarize

    Returns:
        Instructions for thread summarization
    """
    return f"""To summarize thread {thread_id}:
1. Use gmail_get_thread MCP tool with thread_id: {thread_id}
2. Extract key information:
   - Participants in the conversation
   - Main topics discussed
   - Important action items or decisions
   - Timeline of the conversation
3. Present a concise summary focusing on the most relevant points"""


@tool(
    name="search_emails_by_date",
    description="Construct advanced Gmail search query with date filters, sender, and subject filters",
    input_schema={
        "type": "object",
        "properties": {
            "sender": {
                "type": "string",
                "description": "Email address or name to search for",
                "default": ""
            },
            "subject_keywords": {
                "type": "string",
                "description": "Keywords to search in subject line",
                "default": ""
            },
            "after_date": {
                "type": "string",
                "description": "Search emails after this date in YYYY/MM/DD format",
                "default": ""
            },
            "before_date": {
                "type": "string",
                "description": "Search emails before this date in YYYY/MM/DD format",
                "default": ""
            },
            "days_back": {
                "type": "integer",
                "description": "Number of days back to search (overrides after_date)",
                "default": 0
            }
        },
        "required": []
    }
)
async def search_emails_by_date(
    sender: str = "",
    subject_keywords: str = "",
    after_date: str = "",
    before_date: str = "",
    days_back: int = 0
) -> str:
    """
    Construct advanced Gmail search query with date filters.

    This helper tool builds Gmail search queries with various filters.

    Args:
        sender: Email address or name to search for
        subject_keywords: Keywords to search in subject line
        after_date: Date in YYYY/MM/DD format (emails after this date)
        before_date: Date in YYYY/MM/DD format (emails before this date)
        days_back: Number of days to look back (alternative to after_date)

    Returns:
        Constructed Gmail search query
    """
    query_parts = []

    if sender:
        query_parts.append(f"from:{sender}")

    if subject_keywords:
        query_parts.append(f"subject:{subject_keywords}")

    # Handle date filters
    if days_back > 0:
        date_threshold = datetime.now() - timedelta(days=days_back)
        after_date = date_threshold.strftime("%Y/%m/%d")

    if after_date:
        query_parts.append(f"after:{after_date}")

    if before_date:
        query_parts.append(f"before:{before_date}")

    query = " ".join(query_parts) if query_parts else "in:inbox"

    breakdown = "\n".join(f"- {part}" for part in query_parts) if query_parts else "- No filters applied, searching inbox"

    return f"""Gmail search query constructed: "{query}"

Use the gmail_search_emails MCP tool with this query.

Query breakdown:
{breakdown}
"""


@tool(
    name="format_email_date",
    description="Helper to format relative dates (like 'yesterday', 'last week') to Gmail's YYYY/MM/DD format",
    input_schema={
        "type": "object",
        "properties": {
            "date_str": {
                "type": "string",
                "description": "Relative date string like 'yesterday', 'last week', '3 days ago'"
            }
        },
        "required": ["date_str"]
    }
)
async def format_email_date(date_str: str) -> str:
    """
    Helper to format relative dates for Gmail search.

    Args:
        date_str: Relative date like "yesterday", "last week", "3 days ago"

    Returns:
        Formatted date in YYYY/MM/DD format
    """
    now = datetime.now()
    date_lower = date_str.lower().strip()

    if "today" in date_lower:
        target_date = now
    elif "yesterday" in date_lower:
        target_date = now - timedelta(days=1)
    elif "last week" in date_lower or "week ago" in date_lower:
        target_date = now - timedelta(days=7)
    elif "last month" in date_lower or "month ago" in date_lower:
        target_date = now - timedelta(days=30)
    elif "days ago" in date_lower:
        try:
            days = int(date_lower.split()[0])
            target_date = now - timedelta(days=days)
        except (ValueError, IndexError):
            return f"Could not parse '{date_str}'. Use format like '3 days ago'"
    else:
        return f"Could not parse '{date_str}'. Supported: today, yesterday, last week, last month, X days ago"

    return target_date.strftime("%Y/%m/%d")


# Create the SDK MCP server with all custom tools
gmail_helper_server = create_sdk_mcp_server(
    name="gmail_helpers",
    version="1.0.0",
    tools=[
        check_inbox,
        summarize_email_thread,
        search_emails_by_date,
        format_email_date,
    ]
)
