# Clarvis

AI Home Assistant powered by Claude agents, integrating with Home Assistant for voice-controlled automation.

## Overview

Clarvis uses Claude-powered agents with MCP (Model Context Protocol) servers to provide intelligent email access and other home automation capabilities. The system is designed to run on a Windows host (MINISFORUM UN100P with Windows 11 Pro) hosting Home Assistant OS via Hyper-V.

## Quick Start

### Prerequisites

- Python 3.12+ (not 3.14 - missing wheels for some dependencies)
- Node.js 18+ (for npx/MCP servers)
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/jhcahoon/clarvis.git
cd clarvis

# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate     # Linux/Mac
.venv\Scripts\activate        # Windows
```

### Configuration

1. **Copy the example config:**
   ```bash
   cp configs/mcp_servers.json.example configs/mcp_servers.local.json
   ```

2. **Edit `configs/mcp_servers.local.json`** with your platform-specific paths:

   **Mac/Linux:**
   ```json
   {
     "mcpServers": {
       "gmail": {
         "command": "npx",
         "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
         "env": {
           "GMAIL_OAUTH_PATH": "~/.gmail-mcp/gcp-oauth.keys.json",
           "GMAIL_CREDENTIALS_PATH": "~/.gmail-mcp/credentials.json"
         }
       }
     }
   }
   ```

   **Windows:**
   ```json
   {
     "mcpServers": {
       "gmail": {
         "command": "npx",
         "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
         "env": {
           "GMAIL_OAUTH_PATH": "C:\\Users\\YourName\\.gmail-mcp\\gcp-oauth.keys.json",
           "GMAIL_CREDENTIALS_PATH": "C:\\Users\\YourName\\.gmail-mcp\\credentials.json"
         }
       }
     }
   }
   ```

3. **Set up Gmail OAuth credentials** - See [Gmail Setup](#gmail-setup) below.

## Gmail Setup

### 1. Create Google Cloud OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Go to **APIs & Services > Credentials**
5. Click **Create Credentials > OAuth 2.0 Client ID**
6. Select **Desktop App** as application type
7. Download the JSON file

### 2. Place Credentials

```bash
# Create the credentials directory
mkdir -p ~/.gmail-mcp

# Copy your downloaded credentials
cp ~/Downloads/client_secret_*.json ~/.gmail-mcp/gcp-oauth.keys.json
cp ~/.gmail-mcp/gcp-oauth.keys.json ~/.gmail-mcp/credentials.json
```

### 3. Complete OAuth Flow

```bash
npx @gongrzhe/server-gmail-autoauth-mcp auth
```

This will open a browser for Google OAuth consent. After authorization, a `token.json` file will be created.

## Usage

### Interactive Gmail Agent

```bash
python -m clarvis_agents.gmail_agent
```

### API Server (for Home Assistant)

```bash
# Start the server
python scripts/run_api_server.py

# With custom port
python scripts/run_api_server.py --port 8080

# With auto-reload (development)
python scripts/run_api_server.py --reload
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI documentation |
| `/api/v1/gmail/query` | POST | Query Gmail agent |

**Example query:**
```bash
curl -X POST http://localhost:8000/api/v1/gmail/query \
  -H "Content-Type: application/json" \
  -d '{"query": "List my 3 most recent unread emails"}'
```

## Project Structure

```
clarvis/
├── clarvis_agents/
│   ├── gmail_agent/     # Gmail agent implementation
│   │   ├── agent.py     # GmailAgent class
│   │   ├── config.py    # Configuration and rate limiting
│   │   ├── prompts.py   # System prompts
│   │   └── tools.py     # Helper tools
│   └── api/             # FastAPI server
│       ├── server.py    # FastAPI app
│       ├── config.py    # API configuration
│       └── routes/      # API endpoints
├── configs/
│   ├── mcp_servers.json.example    # Template config (committed)
│   ├── mcp_servers.local.json      # Your local config (gitignored)
│   ├── gmail_agent_config.json     # Agent settings
│   └── api_config.json             # API server settings
├── scripts/
│   ├── run_api_server.py           # API server launcher
│   ├── setup_gmail_auth.py         # Gmail OAuth setup wizard
│   └── exploratory/                # Debug and test scripts
└── tests/                          # Test suite
```

## Development

```bash
# Run tests
pytest tests/ -v

# Run specific tests
pytest tests/test_gmail_agent.py -v

# Code quality
ruff check clarvis_agents/
black clarvis_agents/
mypy clarvis_agents/
```

## License

MIT
