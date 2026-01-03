# Gmail Agent

A Gmail-checking agent built with the Claude Agent SDK that provides natural language access to your Gmail inbox.

## Features

- **Natural Language Queries**: Ask about your emails in plain English
- **Read-Only Mode**: Safe by default with code-enforced read-only permissions
- **Advanced Search**: Search by sender, subject, date, keywords, and more
- **Thread Summarization**: Get concise summaries of email conversations
- **Rate Limiting**: Built-in protection against API quota exhaustion
- **Audit Logging**: Complete audit trail of all email access
- **Interactive CLI**: Command-line interface for testing and development

## Quick Start

### 1. Install MCP Server

```bash
npx -y @smithery/cli install @gongrzhe/server-gmail-autoauth-mcp --client claude
```

### 2. Set Up OAuth Credentials

Run the setup wizard:

```bash
python scripts/setup_gmail_auth.py
```

This will guide you through:
- Creating a Google Cloud project
- Enabling the Gmail API
- Creating OAuth 2.0 credentials
- Placing credentials in the correct location

### 3. Run the Agent

**Interactive Mode:**
```bash
# Activate virtual environment first
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Run the agent
python -m clarvis_agents.gmail_agent
```

**Programmatic Usage:**
```python
from clarvis_agents.gmail_agent import create_gmail_agent

agent = create_gmail_agent()
response = agent.check_emails("Check my unread emails")
print(response)
```

## Context Retention

The Gmail Agent supports two modes of operation with different context retention behaviors:

### Interactive Mode (Context Retained)

When running `python -m clarvis_agents.gmail_agent`, the agent maintains conversation context throughout the entire session. You can ask follow-up questions that reference previous exchanges:

```bash
$ python -m clarvis_agents.gmail_agent

You: Show me unread emails from last week
Agent: [Lists 5 emails from various senders]

You: What's the most important one?  # ✅ Agent remembers the 5 emails
Agent: [Analyzes and identifies the most important email]

You: Summarize it for me  # ✅ Still knows which email
Agent: [Provides summary of that specific email]

You: Draft a reply  # ✅ Full context retained
Agent: [Drafts reply based on the email content]
```

**How it works:** The agent uses `ClaudeSDKClient` to maintain a stateful session. All queries within one CLI session share the same conversation context.

**Session lifecycle:**
- **Start**: When you run `python -m clarvis_agents.gmail_agent`
- **Active**: All queries in that session have context
- **End**: When you type `quit` or close the terminal

### Programmatic Mode (Stateless)

The `check_emails()` method is stateless - each call is independent with no memory of previous calls. This is intentional for simplicity in scripts and automation:

```python
agent = create_gmail_agent()

# Each call is independent
agent.check_emails("Show me emails from John")  # Query 1
agent.check_emails("What was the last one about?")  # ❌ No context - won't know what "last one" means
```

**When to use programmatic mode:**
- One-off email checks in scripts
- Automation workflows with single queries
- When you don't need conversation context

**When to use interactive mode:**
- Multi-turn conversations about emails
- Complex email analysis workflows
- Testing and development

## Usage Examples

### Check Unread Emails
```python
agent.check_emails("Check my unread emails")
# Returns summary of unread emails with sender, subject, date
```

### Search by Sender
```python
agent.check_emails("Show me emails from john@company.com")
# Searches for all emails from specific sender
```

### Search by Date Range
```python
agent.check_emails("Show me emails from last week")
# Searches emails from the past 7 days
```

### Advanced Search
```python
agent.check_emails("Find emails from boss@company.com about budget from last month")
# Combines multiple filters: sender, subject keywords, and date range
```

### Summarize Thread
```python
agent.check_emails("Summarize the thread about project updates")
# Finds relevant thread and provides concise summary
```

### Find Urgent Emails
```python
agent.check_emails("Do I have any urgent emails?")
# Searches for emails with urgency indicators
```

## Gmail Search Syntax

The agent understands Gmail's advanced search operators:

| Operator | Example | Description |
|----------|---------|-------------|
| `from:` | `from:john@example.com` | Emails from specific sender |
| `to:` | `to:me@example.com` | Emails to specific recipient |
| `subject:` | `subject:budget` | Emails with keywords in subject |
| `after:` | `after:2025/01/01` | Emails after date (YYYY/MM/DD) |
| `before:` | `before:2025/12/31` | Emails before date |
| `has:attachment` | `has:attachment` | Emails with attachments |
| `is:unread` | `is:unread` | Unread emails |
| `is:read` | `is:read` | Read emails |
| `in:inbox` | `in:inbox` | Emails in inbox |
| `label:` | `label:work` | Emails with specific label |

Combine operators with spaces (implicit AND):
```
from:john@example.com subject:budget after:2025/11/01
```

## Configuration

### Agent Configuration

Edit `configs/gmail_agent_config.json`:

```json
{
  "agent": {
    "model": "claude-haiku-4-5-20250429",
    "max_turns": 30
  },
  "permissions": {
    "read_only": true
  },
  "rate_limits": {
    "max_emails_per_search": 50,
    "max_searches_per_minute": 10
  }
}
```

### Programmatic Configuration

```python
from agents.gmail_agent import GmailAgent, GmailAgentConfig

config = GmailAgentConfig(
    model="claude-sonnet-4-5",  # Use Sonnet for complex tasks
    max_turns=50,
    read_only=True,
    max_searches_per_minute=20
)

agent = GmailAgent(config)
```

## Security & Privacy

### Read-Only Mode

By default, the agent operates in read-only mode. The following tools are blocked:

- `gmail_send_email` - Cannot send emails
- `gmail_delete_email` - Cannot delete emails
- `gmail_modify_labels` - Cannot modify labels
- `gmail_trash_email` - Cannot trash emails

### OAuth Credentials

Credentials are stored securely:

```
~/.gmail-mcp/
├── credentials.json (600 permissions - owner read/write only)
├── token.json (auto-generated on first auth)
└── .gitignore (prevents accidental commits)
```

### Audit Logging

All email access is logged to `logs/gmail_agent/access_YYYYMMDD.log`:

```json
{
  "timestamp": "2025-12-26T10:30:00Z",
  "tool": "gmail_search_emails",
  "params": {"query": "from:john@example.com"},
  "user": "your_username",
  "success": true
}
```

### Rate Limiting

Default limits:
- **10 searches per minute** (configurable)
- **50 emails per search** (configurable)

Gmail API quotas:
- 1 billion quota units per day
- 250 quota units per second per user

## Testing

### Run Unit Tests

```bash
pytest tests/test_gmail_agent.py -v
```

### Run Integration Tests

Integration tests require Gmail credentials:

```bash
pytest tests/test_gmail_agent.py -v -m integration
```

### Test Coverage

```bash
pytest tests/test_gmail_agent.py --cov=agents.gmail_agent --cov-report=html
```

## Troubleshooting

### MCP Server Won't Start

**Check Node.js/npx:**
```bash
node --version
npx --version
```

**Reinstall MCP Server:**
```bash
npx -y @smithery/cli install @gongrzhe/server-gmail-autoauth-mcp --client claude --force
```

**Check Logs:**
```bash
mcp logs gmail
```

### OAuth Authentication Fails

**Validate credentials JSON:**
```bash
cat ~/.gmail-mcp/credentials.json | python -m json.tool
```

**Re-authenticate:**
```bash
rm ~/.gmail-mcp/token.json
# Next agent run will trigger OAuth flow
```

**Common Issues:**
- Gmail API not enabled in Google Cloud Console
- OAuth scope doesn't include `gmail.modify`
- Credentials for wrong application type (need "Desktop App")

### "Insufficient Permissions" Error

1. Go to Google Cloud Console
2. Verify Gmail API is enabled
3. Check OAuth 2.0 Client ID settings
4. Ensure scope includes `https://www.googleapis.com/auth/gmail.modify`
5. Re-download credentials and run setup again

### Rate Limit Exceeded

**Check usage:**
- Go to Google Cloud Console > APIs & Services > Dashboard
- View quota usage for Gmail API

**Adjust limits:**
```python
config = GmailAgentConfig(max_searches_per_minute=5)
agent = GmailAgent(config)
```

**Implement backoff:**
The agent will automatically reject requests over the rate limit. Wait 60 seconds and try again.

### Agent Returns Empty or Incomplete Response

**Possible causes:**
1. No emails match the search criteria
2. MCP server connection issue
3. Model token limit reached (increase max_turns)

**Debug:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

agent = create_gmail_agent()
response = agent.check_emails("your query")
```

Check `logs/gmail_agent/access_YYYYMMDD.log` for details.

## Performance

### Model Selection

**Haiku 4.5 (Default):**
- Latency: ~1-2 seconds
- Cost: $0.01 per 1K input tokens
- Best for: Routine email checking, searching, basic summarization

**Sonnet 4.5:**
- Latency: ~3-5 seconds
- Cost: Higher per token
- Best for: Complex categorization, sentiment analysis, multi-step workflows

**Switch to Sonnet:**
```python
config = GmailAgentConfig(model="claude-sonnet-4-5-20250429")
agent = GmailAgent(config)
```

### Optimization Tips

1. **Use specific search queries** - Narrow results with precise filters
2. **Limit results** - Default is 50 emails max per search
3. **Cache results** - Email content doesn't change frequently
4. **Batch operations** - Group related queries together

## Project Structure

```
agents/gmail_agent/
├── __init__.py
├── agent.py          # Main agent class
├── config.py         # Configuration and rate limiting
├── tools.py          # Custom helper tools
└── prompts.py        # System prompts

configs/
├── gmail_agent_config.json   # Agent configuration
└── mcp_servers.json          # MCP server registry

scripts/
└── setup_gmail_auth.py       # OAuth setup wizard

tests/
└── test_gmail_agent.py       # Unit and integration tests

logs/gmail_agent/
└── access_YYYYMMDD.log       # Audit logs
```

## Future Enhancements

### Planned Features

- **Calendar Integration**: Create calendar events from emails
- **Task Creation**: Convert emails to tasks
- **Smart Categorization**: Auto-label emails (requires Sonnet)
- **Daily Digest**: Scheduled email summaries
- **Attachment Download**: Save attachments locally
- **Multi-language Support**: Email queries in multiple languages

### Home Assistant Integration

When ready for Phase 1 Week 3-4:

```python
from agents.gmail_agent import GmailAgent

class HomeAssistantGmailAgent(GmailAgent):
    """Wraps GmailAgent with HA conversation agent interface"""

    async def async_process(self, user_input: str) -> str:
        return await self._check_emails_async(user_input)
```

### AWS Deployment

Containerization-ready for Phase 2:

```dockerfile
FROM python:3.11-slim
RUN npm install -g npx
COPY . /app
RUN pip install -r requirements.txt
ENV GMAIL_CREDENTIALS_PATH=/secrets/credentials.json
CMD ["python", "-m", "agents.gmail_agent"]
```

## Contributing

### Development Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov ruff black mypy

# Run tests
pytest tests/test_gmail_agent.py -v
```

### Code Style

```bash
# Format code
black agents/gmail_agent/

# Lint
ruff check agents/gmail_agent/

# Type check
mypy agents/gmail_agent/
```

## License

This project is part of the Clarvis AI Home Assistant system.

## Support

For issues and questions:
1. Check the Troubleshooting section above
2. Review agent logs in `logs/gmail_agent/`
3. Open an issue in the project repository
4. Consult [Claude Agent SDK documentation](https://docs.anthropic.com/claude/docs/agents)

## Version

**Version:** 1.0.0
**Last Updated:** 2025-12-28
**Claude Agent SDK:** 0.4.2
**Compatible with:** Phase 1 of AI Home Assistant Project
