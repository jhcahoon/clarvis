# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Clarvis is an AI Home Assistant project that integrates Claude-powered agents with Home Assistant for voice-controlled automation. The system runs on a MINISFORUM UN100P with Windows 11 Pro hosting Home Assistant OS via Hyper-V.

## Development Commands

```bash
# Activate virtual environment
source .venv/bin/activate     # Linux/Mac
.venv\Scripts\activate        # Windows

# Install dependencies (uses uv package manager)
uv sync

# Run Gmail Agent (interactive mode)
python -m clarvis_agents.gmail_agent

# Run API Server (for Home Assistant integration)
python scripts/run_api_server.py

# Run API Server with custom port
python scripts/run_api_server.py --port 8080

# Run API Server with auto-reload (development)
python scripts/run_api_server.py --reload

# Run tests
pytest tests/ -v

# Run specific tests
pytest tests/test_gmail_agent.py -v

# Run integration tests (requires Gmail credentials)
pytest tests/test_gmail_agent.py -v -m integration

# Code quality
ruff check clarvis_agents/
black clarvis_agents/
mypy clarvis_agents/
```

## Architecture

### Agent Pattern

Agents use the Claude Agent SDK with MCP (Model Context Protocol) servers for external integrations:

```
clarvis_agents/
└── gmail_agent/
    ├── agent.py      # GmailAgent class with ClaudeSDKClient
    ├── config.py     # GmailAgentConfig, RateLimiter
    ├── prompts.py    # System prompts
    └── tools.py      # Helper tools
```

**Key architectural decisions:**
- Agents use `ClaudeSDKClient` for stateful sessions (interactive mode) or `query()` for stateless operations
- MCP servers spawn via subprocess (stdio type) using npx
- Rate limiting implemented via sliding window algorithm in `RateLimiter` class
- Read-only mode enforced by blocking specific MCP tools (send, delete, modify)

### API Server

The API server exposes agents via HTTP for Home Assistant integration:

```
clarvis_agents/
└── api/
    ├── server.py         # FastAPI app
    ├── config.py         # APIConfig dataclass
    └── routes/
        ├── health.py     # GET /health
        └── gmail.py      # POST /api/v1/gmail/query
```

**Endpoints:**
- `GET /health` - Health check
- `GET /docs` - Swagger UI documentation
- `POST /api/v1/gmail/query` - Query Gmail agent

### Configuration

- `configs/gmail_agent_config.json` - Agent settings, permissions, rate limits
- `configs/api_config.json` - API server settings (host, port, CORS)
- `configs/mcp_servers.json` - MCP server registry with command/args/env
- `.env` - API keys (copy from `.env.example`)

### MCP Integration Pattern

```python
# From agent.py - MCP server configuration
options = ClaudeAgentOptions(
    mcp_servers={
        "gmail": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
            "env": {...}
        }
    },
    extra_args={"dangerously-skip-permissions": None}  # Required for MCP
)
```

### Gmail Credentials

OAuth credentials stored in `~/.gmail-mcp/`:
- `gcp-oauth.keys.json` - Google Cloud OAuth keys
- `credentials.json` - User credentials
- `token.json` - Auto-generated OAuth token

Run `python scripts/setup_gmail_auth.py` for OAuth setup wizard.

## Future Agents (Planned)

Per project plan, additional agents for: Calendar, Weather, Local Events. Email agent runs locally for privacy; others may deploy to AWS Lambda.

## Dependencies

Python 3.12+, managed via `uv`. Key packages:
- `claude-agent-sdk` - Core agent framework
- `anthropic` - Claude API client
- `mcp` - Model Context Protocol
- Gmail MCP: `@gongrzhe/server-gmail-autoauth-mcp` (installed via npx)
