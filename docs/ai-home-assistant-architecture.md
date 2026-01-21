# AI Home Assistant - Technical Architecture

**Last Updated:** January 21, 2026 (v2.15)

---

## Table of Contents
1. [Infrastructure Overview](#infrastructure-overview)
2. [Local Infrastructure](#local-infrastructure)
3. [Clarvis API Server](#clarvis-api-server)
4. [Streaming Architecture](#streaming-architecture)
5. [Network Architecture](#network-architecture)
6. [Cloud Infrastructure](#cloud-infrastructure-future)
7. [Agent Architecture](#agent-architecture)
8. [Security Considerations](#security-considerations)
9. [Evaluation Framework](#evaluation-framework)

---

## Infrastructure Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Home Network                              │
│                                                                  │
│  ┌──────────────────────────────────────────┐                   │
│  │     Host Machine (Windows 11 Pro)        │                   │
│  │     (Mini PC or similar recommended)     │                   │
│  │  ┌────────────────────────────────────┐  │                   │
│  │  │   Hyper-V VM: Home Assistant OS    │  │                   │
│  │  │   - Supervisor                     │  │                   │
│  │  │   - Add-ons (SSH, Samba, etc.)     │  │                   │
│  │  │   - Custom Integrations            │  │                   │
│  │  └──────────────┬─────────────────────┘  │                   │
│  │                 │ HTTP :8000             │                   │
│  │                 ▼                        │                   │
│  │  ┌────────────────────────────────────┐  │                   │
│  │  │   Windows Host (<YOUR_HOST_IP>)    │  │                   │
│  │  │   - Clarvis API Server (FastAPI)   │  │                   │
│  │  │   - Gmail Agent + MCP Server       │  │                   │
│  │  │   - Development environment        │  │                   │
│  │  └────────────────────────────────────┘  │                   │
│  └──────────────────────────────────────────┘                   │
│                          │                                       │
│              Home Assistant Bridge                               │
│             (Hyper-V Virtual Switch)                            │
│                          │                                       │
│  ┌──────────────────────────────────────────┐                   │
│  │     Home Assistant Voice PE              │                   │
│  │     - Wake word detection                │                   │
│  │     - Audio I/O                          │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Internet
                              ▼
                    ┌─────────────────┐
                    │   AWS Cloud     │
                    │   (Future)      │
                    └─────────────────┘
```

---

## Local Infrastructure

### Host Machine Requirements

| Spec | Recommended |
|------|-------------|
| CPU | Intel N100 or better (4+ cores) |
| RAM | 8-16 GB DDR4 |
| Storage | 128+ GB SSD |
| OS | Windows 11 Pro (for Hyper-V support) |
| Network | Ethernet recommended (Wi-Fi supported) |

> **Note:** Low-power mini PCs (e.g., Intel N100-based systems) work well for this use case, providing quiet 24/7 operation with minimal power consumption.

**Responsibilities:**
- Host Hyper-V hypervisor
- Run Home Assistant OS VM
- Development environment for agents
- Run MCP servers locally
- Local agent execution (privacy-sensitive operations)

### Virtualization: Hyper-V

**Why Hyper-V:**
- Native to Windows 11 Pro (no additional software)
- Type 1 hypervisor characteristics (runs under Windows)
- Better performance than VirtualBox/VMware for this use case
- Native External Virtual Switch for network bridging
- Good integration with Windows development tools

**VM Configuration:**

| Setting | Value |
|---------|-------|
| Name | Home Assistant |
| Generation | 2 |
| RAM | 4 GB (Dynamic Memory enabled) |
| Processors | 2 virtual CPUs |
| Disk | 64 GB (expandable VHDX) |
| Network | External Virtual Switch (bridged) |
| Secure Boot | Disabled (required for HAOS) |
| Auto-Start | Enabled (starts with Windows) |

### Home Assistant OS (HAOS)

**Current Versions (as of January 2026):**

| Component | Version |
|-----------|---------|
| Core | 2025.12.5 |
| Supervisor | 2025.12.3 |
| Operating System | 16.3 |
| Frontend | 20251203.3 |

**Core Components:**
- Home Assistant Core - main automation platform
- Supervisor - manages add-ons and system
- Operating System - minimal Linux base

**Installed Add-ons:**
- [x] Terminal & SSH - CLI access
- [x] Samba share - Windows file access at `\\homeassistant.local\config`
- [ ] File Editor - in-browser config editing
- [ ] Studio Code Server - VS Code in browser (optional)

**Custom Integrations:**
- Clarvis conversation agent (`custom_components/clarvis/`)

### Voice Hardware: Home Assistant Voice PE

| Spec | Value |
|------|-------|
| Wake Word Engine | microWakeWord (on-device) |
| Default Wake Word | "Hey Nabu" |
| Audio | Dual microphones, speaker |
| Connection | Wi-Fi to local network |

**Voice Pipeline:**
```
Wake Word → STT (Whisper) → Clarvis Agent → TTS (Piper) → Audio
    │            │               │                │
    └── Device ──┴───────────────┼────────────────┘
                                 │
                         ┌───────▼────────┐
                         │ Clarvis API    │
                         │ (SSE Stream)   │
                         └────────────────┘
```

**Streaming Pipeline (HA 2025.7+):**
```
Voice → STT → Clarvis Component ──SSE──▶ API ──stream()──▶ Agent
                    │
                    └──ChatLog.async_add_delta_content_stream()──▶ TTS (streaming)
```

---

## Clarvis API Server

The Clarvis API Server exposes AI agents via HTTP REST endpoints, enabling Home Assistant to query agents for natural language processing.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Clarvis API Server                            │
│                    (FastAPI + Uvicorn)                          │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │   Routes    │    │   Agents    │    │    MCP Servers      │  │
│  │             │    │             │    │                     │  │
│  │ /health     │───▶│ GmailAgent  │───▶│ @gongrzhe/server-   │  │
│  │ /api/v1/    │    │             │    │ gmail-autoauth-mcp  │  │
│  │   gmail/    │    │             │    │                     │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
clarvis_agents/
├── api/
│   ├── __init__.py
│   ├── server.py           # FastAPI app with CORS, middleware
│   ├── config.py           # APIConfig dataclass
│   └── routes/
│       ├── __init__.py
│       ├── gmail.py        # POST /api/v1/gmail/query
│       ├── health.py       # GET /health
│       └── orchestrator.py # POST /api/v1/query, /query/stream, GET /agents
├── core/                   # Core abstractions for multi-agent architecture
│   ├── __init__.py         # Exports: BaseAgent, AgentRegistry, ConversationContext
│   ├── base_agent.py       # BaseAgent ABC, AgentResponse, AgentCapability
│   ├── agent_registry.py   # AgentRegistry singleton
│   └── context.py          # ConversationContext, ConversationTurn
├── orchestrator/           # Intent classification and routing
│   ├── __init__.py         # Exports: IntentClassifier, IntentRouter, OrchestratorAgent, etc.
│   ├── agent.py            # OrchestratorAgent class, create_orchestrator factory
│   ├── classifier.py       # IntentClassifier with keyword/pattern matching
│   ├── config.py           # OrchestratorConfig dataclass
│   ├── router.py           # IntentRouter with hybrid code/LLM routing
│   └── prompts.py          # Router system prompts
├── gmail_agent/
│   ├── __init__.py
│   ├── agent.py            # GmailAgent class (implements BaseAgent)
│   ├── config.py           # GmailAgentConfig, RateLimiter
│   ├── prompts.py          # System prompts
│   └── tools.py            # Helper tools
configs/
├── api_config.json         # API server configuration
├── gmail_agent_config.json # Gmail agent settings
├── orchestrator_config.json # Orchestrator settings
└── mcp_servers.json        # MCP server registry
scripts/
└── run_api_server.py       # Entry point for API server
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root endpoint with API info |
| `/health` | GET | Health check, returns server status and available agents |
| `/docs` | GET | Swagger UI documentation |
| `/api/v1/query` | POST | Query the orchestrator (routes to appropriate agent) |
| `/api/v1/query/stream` | POST | **Stream** response via SSE (Server-Sent Events) |
| `/api/v1/agents` | GET | List available agents and their capabilities |
| `/api/v1/gmail/query` | POST | Query the Gmail agent directly (bypasses orchestrator) |

### Configuration

**File:** `configs/api_config.json`
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "cors_origins": ["*"],
    "debug": false
  },
  "agents": {
    "gmail": {
      "enabled": true,
      "timeout_seconds": 120
    },
    "orchestrator": {
      "enabled": true,
      "timeout_seconds": 180
    }
  }
}
```

**File:** `configs/orchestrator_config.json`
```json
{
  "orchestrator": {
    "model": "claude-sonnet-4-20250514",
    "router_model": "claude-3-5-haiku-20241022",
    "session_timeout_minutes": 30,
    "max_turns": 5
  },
  "routing": {
    "code_routing_threshold": 0.7,
    "llm_routing_enabled": true,
    "follow_up_detection": true,
    "default_agent": null
  },
  "agents": {
    "gmail": { "enabled": true, "priority": 1 },
    "calendar": { "enabled": false, "priority": 2 },
    "weather": { "enabled": false, "priority": 3 },
    "events": { "enabled": false, "priority": 4 }
  },
  "logging": {
    "level": "INFO",
    "log_routing_decisions": true,
    "log_agent_responses": true
  }
}
```

**Orchestrator Configuration Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `model` | claude-sonnet-4 | Model for direct responses |
| `router_model` | claude-3-5-haiku | Model for LLM routing (can be faster/cheaper) |
| `session_timeout_minutes` | 30 | Session expiry time |
| `max_turns` | 5 | Maximum conversation turns per session |
| `code_routing_threshold` | 0.7 | Confidence threshold for code-based routing |
| `llm_routing_enabled` | true | Enable LLM fallback routing |
| `follow_up_detection` | true | Detect and route follow-up queries |
| `default_agent` | null | Default agent when routing is ambiguous |
| `log_routing_decisions` | true | Log all routing decisions |
| `log_agent_responses` | true | Log agent responses |

### Starting the Server

```bash
# Standard startup
python scripts/run_api_server.py

# Custom port
python scripts/run_api_server.py --port 8080

# Development mode with auto-reload
python scripts/run_api_server.py --reload
```

---

## Streaming Architecture

The streaming architecture enables real-time voice responses through Home Assistant's TTS system. When a user speaks a query, the response begins playing as soon as the first words are generated, dramatically reducing perceived latency.

### End-to-End Streaming Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Voice Query Streaming Flow                           │
│                                                                              │
│  ┌──────────┐    ┌────────────┐    ┌────────────────┐    ┌───────────────┐ │
│  │ Voice PE │───▶│    STT     │───▶│  Clarvis HA    │───▶│  Clarvis API  │ │
│  │          │    │  (Whisper) │    │   Component    │    │   (FastAPI)   │ │
│  └──────────┘    └────────────┘    └───────┬────────┘    └───────┬───────┘ │
│                                            │                     │         │
│                                            │   SSE Stream        │         │
│                                            │◀────────────────────┤         │
│                                            │  data: {"text":...} │         │
│                                            │  data: {"text":...} │         │
│                                            │  data: [DONE]       │         │
│                                            │                     │         │
│                                            ▼                     ▼         │
│  ┌──────────┐    ┌────────────┐    ┌────────────────┐    ┌───────────────┐ │
│  │ Voice PE │◀───│    TTS     │◀───│    ChatLog     │◀───│  Orchestrator │ │
│  │ (Speaker)│    │  (Piper)   │    │   (HA 2025.7+) │    │   stream()    │ │
│  └──────────┘    └────────────┘    └────────────────┘    └───────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Streaming Components

#### 1. API Server: SSE Streaming Endpoint

**Endpoint:** `POST /api/v1/query/stream`

The streaming endpoint uses Server-Sent Events (SSE) to push response chunks as they're generated:

```
Content-Type: text/event-stream

data: {"text": "You have ", "session_id": "abc123"}

data: {"text": "3 unread emails.", "session_id": "abc123"}

data: [DONE]
```

**Implementation:** `clarvis_agents/api/routes/orchestrator.py`
- Uses FastAPI's `StreamingResponse` with `text/event-stream` media type
- Includes headers to disable buffering (`X-Accel-Buffering: no` for nginx)
- Async generator yields JSON-encoded chunks

#### 2. Orchestrator Streaming

**Implementation:** `clarvis_agents/orchestrator/agent.py`

The `OrchestratorAgent` implements streaming through the `stream()` method:

```python
async def stream(self, query, context) -> AsyncGenerator[str, None]:
    decision = await self._router.route(query, context)

    if decision.handle_directly:
        async for chunk in self._stream_direct(query, context):
            yield chunk
    elif decision.agent_name:
        async for chunk in self._stream_single_agent(query, decision, context):
            yield chunk
    else:
        async for chunk in self._stream_fallback(query, context):
            yield chunk
```

**Streaming Methods:**
- `_stream_direct()` - Uses Anthropic's `messages.stream()` for direct handling
- `_stream_single_agent()` - Delegates to agent's `stream()` method
- `_stream_fallback()` - Yields fallback message in one chunk

#### 3. Agent Streaming Interface

**Implementation:** `clarvis_agents/core/base_agent.py`

The `BaseAgent` abstract class defines an optional `stream()` method:

```python
async def stream(self, query, context) -> AsyncGenerator[str, None]:
    """Stream response chunks for a query.

    Default implementation falls back to process() and yields
    the complete response as a single chunk.
    """
    response = await self.process(query, context)
    yield response.content
```

Agents can override this to provide true streaming:

- **GmailAgent**: Streams chunks from Claude SDK as they arrive
- **Future agents**: Can implement streaming or use the default fallback

#### 4. Home Assistant ChatLog Integration

**Implementation:** `homeassistant/custom_components/clarvis/conversation.py`

The Clarvis conversation entity uses Home Assistant's ChatLog API (HA 2025.7+) for streaming TTS:

```python
class ClarvisConversationEntity(ConversationEntity):
    _attr_supports_streaming = True  # Enable HA streaming TTS

    async def _async_handle_message(self, user_input, chat_log):
        async def _transform_stream():
            yield AssistantContentDeltaDict(role="assistant")
            async for chunk in self._stream_from_api(user_input):
                yield AssistantContentDeltaDict(content=chunk)

        async for _ in chat_log.async_add_delta_content_stream(
            self.entity_id, _transform_stream()
        ):
            pass

        return async_get_result_from_chat_log(user_input, chat_log)
```

**Key Features:**
- Detects ChatLog API availability at runtime (graceful degradation)
- Transforms SSE events to HA's `AssistantContentDeltaDict` format
- Feeds chunks directly to TTS for immediate playback

### Smart Fallback to Home Assistant

The component intelligently routes queries to Home Assistant's default agent when appropriate:

**Home Assistant Command Keywords** (`homeassistant/custom_components/clarvis/const.py`):
```python
HA_COMMAND_KEYWORDS = [
    "turn on", "turn off", "switch on", "switch off",
    "dim", "brighten", "set temperature", "lock", "unlock",
    "open", "close", "arm", "disarm", "play", "pause", "stop",
    "volume", "mute", "unmute"
]
```

**Fallback Logic:**
1. If orchestrator returns a "fallback" response (no agent matched)
2. AND the query matches HA command keywords
3. THEN delegate to HA's built-in agent for device control

This ensures device commands like "turn on the living room light" are handled by Home Assistant's native capabilities.

### Version Compatibility

| Home Assistant Version | Streaming Support | Notes |
|----------------------|-------------------|-------|
| 2025.7+ | ✅ Full streaming | ChatLog API with `async_add_delta_content_stream()` |
| Earlier versions | ⚠️ Fallback mode | Non-streaming, waits for complete response |

The component automatically detects the available API and degrades gracefully on older versions.

---

## Network Architecture

### Network Topology

```
Internet
    │
    ▼
┌─────────────────────────────────────────┐
│            Home Router                   │
│         (DHCP Server)                    │
│         Subnet: 10.0.0.0/24             │
└─────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    ┌─────────┐   ┌──────────┐   ┌──────────┐
    │ Windows │   │   HAOS   │   │ Voice PE │
    │  Host   │   │    VM    │   │          │
    │<YOUR_HOST_IP>│   │  (DHCP)  │   │  (DHCP)  │
    │ :8000   │   │  :8123   │   │          │
    └─────────┘   └──────────┘   └──────────┘
         ▲              │
         │   HTTP API   │
         └──────────────┘
```

### Hyper-V Virtual Switch Configuration

**Switch Name:** `Home Assistant Bridge`
**Type:** External
**Binding:** Physical network adapter (WiFi - Ethernet migration planned, see Issue #8)
**Sharing:** Management OS shares adapter
**Network Profile:** Public (requires firewall rule to include Public profile)

This configuration gives the VM its own IP address on the home network, allowing:
- Voice PE to communicate directly with Home Assistant
- Home Assistant to communicate with Clarvis API on Windows host
- mDNS discovery (`homeassistant.local`)
- Access from any device on the network

### Ports & Protocols

| Service | Port | Protocol | Direction | Notes |
|---------|------|----------|-----------|-------|
| Clarvis API Server | 8000 | HTTP | Inbound | Windows host, firewall rule required |
| Home Assistant Web UI | 8123 | HTTP/HTTPS | Inbound | HAOS VM |
| SSH (if enabled) | 22 | TCP | Inbound | HAOS VM |
| Samba | 445 | TCP | Inbound | HAOS VM |
| mDNS | 5353 | UDP | Both | - |
| Wyoming (Voice) | 10400 | TCP | Internal | - |

### Windows Firewall Configuration

A firewall rule is required for the Clarvis API Server:

**Rule Name:** `Clarvis API Server`
**Direction:** Inbound
**Protocol:** TCP
**Port:** 8000
**Profiles:** Private, Public

```powershell
# Create rule (run as Administrator)
New-NetFirewallRule -DisplayName 'Clarvis API Server' `
    -Direction Inbound -Protocol TCP -LocalPort 8000 `
    -Action Allow -Profile Private,Public
```

### DNS/Discovery

- **mDNS:** Home Assistant advertises as `homeassistant.local`
- **Windows Host:** Access via IP `<YOUR_HOST_IP>` (mDNS not available)
- **Fallback:** Use direct IP if mDNS doesn't resolve
- **Voice PE Discovery:** Auto-discovered via Zeroconf/mDNS

---

## Cloud Infrastructure (Future)

### AWS Architecture (Planned - Phase 2)

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │ API Gateway │───▶│   Lambda    │───▶│ Secrets Manager     │  │
│  │             │    │  Functions  │    │ (API Keys)          │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│         │                  │                                     │
│         │                  ▼                                     │
│         │           ┌─────────────┐                             │
│         │           │  Bedrock /  │                             │
│         │           │ Claude API  │                             │
│         │           └─────────────┘                             │
│         │                  │                                     │
│         ▼                  ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    CloudWatch                                ││
│  │              (Logging & Monitoring)                          ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Agent Deployment Strategy

| Agent | Location | Reason |
|-------|----------|--------|
| Email Agent | Local (UN100P) | Privacy - email content stays local |
| Calendar Agent | AWS Lambda | Low sensitivity, benefits from cloud |
| Weather Agent | AWS Lambda | Public data, stateless |
| Events Agent | AWS Lambda | Public data, stateless |
| Router/Orchestrator | Local (UN100P) | Low latency, controls routing |

### API Strategy (Decision Pending)

**Option A: Direct Anthropic API**
- Latest Claude features
- Simpler architecture
- Pay-per-use pricing

**Option B: AWS Bedrock**
- Integrated with AWS services
- Consolidated AWS billing
- Regional compliance
- May lack newest features

**Decision:** To be evaluated in Phase 2

---

## Agent Architecture

For detailed documentation on the multi-agent orchestration pattern, core abstractions (BaseAgent, AgentRegistry, ConversationContext), routing logic, and how to add new agents, see **[Agent Architecture](agent_architecture.md)**.

### Current Implementation

The Gmail Agent, Ski Agent, and Notes Agent are fully implemented and accessible via the Clarvis API Server.

```
┌──────────────┐     ┌───────────────────┐     ┌─────────────────┐
│  Voice PE    │────▶│  Home Assistant   │────▶│  Clarvis API    │
│              │     │  (Intent Parse)   │     │  (FastAPI)      │
└──────────────┘     └───────────────────┘     └─────────────────┘
                                                       │
                                                       ▼
                                               ┌─────────────┐
                                               │ GmailAgent  │
                                               │  (Local)    │
                                               │     │       │
                                               │     ▼       │
                                               │  MCP Server │
                                               │  (Gmail)    │
                                               └─────────────┘
```

### Gmail Agent

**Location:** `clarvis_agents/gmail_agent/`

**Implements:** `BaseAgent` interface (can be registered with orchestrator)

**Features:**
- Natural language email queries via Claude Agent SDK
- MCP (Model Context Protocol) integration for Gmail access
- Read-only mode for safety (blocks send/delete/modify operations)
- Rate limiting via sliding window algorithm
- OAuth authentication via `~/.gmail-mcp/` credentials
- **Streaming support** via `stream()` method for real-time TTS

**Capabilities:**
- `check_inbox` - Check inbox for new or unread emails
- `search_emails` - Search emails by sender, subject, date, or keywords
- `read_email` - Read full email content and threads
- `summarize` - Summarize emails or threads

**Usage:**
```python
from clarvis_agents.gmail_agent import GmailAgent

agent = GmailAgent(read_only=True)
response = agent.check_emails("How many unread emails do I have?")
```

**API Access:**
```bash
curl -X POST http://<YOUR_HOST_IP>:8000/api/v1/gmail/query \
     -H "Content-Type: application/json" \
     -d '{"query": "check my unread emails"}'
```

### Ski Agent

**Location:** `clarvis_agents/ski_agent/`

**Implements:** `BaseAgent` interface (can be registered with orchestrator)

**Features:**
- Ski conditions reporting for Mt Hood Meadows
- Native SDK tools with `httpx` for fast web fetching (no external MCP server)
- Rate limiting via sliding window algorithm
- Caching of conditions data to minimize requests
- **Streaming support** via `stream()` method for real-time TTS

**Capabilities:**
- `snow_conditions` - Report snow depths and recent snowfall
- `lift_status` - Report which lifts are open or on hold
- `weather` - Report mountain weather conditions
- `full_report` - Comprehensive ski conditions report

**Data Source:** `https://cloudserv.skihood.com/`

**Usage:**
```python
from clarvis_agents.ski_agent import SkiAgent

agent = SkiAgent()
response = agent.get_conditions("What's the ski report at Meadows?")
```

**API Access:**
```bash
curl -X POST http://<YOUR_HOST_IP>:8000/api/v1/query \
     -H "Content-Type: application/json" \
     -d '{"query": "what is the ski report at meadows"}'
```

**Voice Examples:**
- "What's the ski report at Meadows?"
- "How much snow at Hood?"
- "Are the lifts running?"
- "What's the powder like?"

### Notes Agent

**Location:** `clarvis_agents/notes_agent/`

**Implements:** `BaseAgent` interface (can be registered with orchestrator)

**Features:**
- Manage notes, lists, reminders, and quick information
- Native SDK tools for direct file I/O (no external MCP server)
- JSON file storage in `~/.clarvis/notes/`
- Fuzzy matching for note names
- Rate limiting via sliding window algorithm
- **Streaming support** via `stream()` method for real-time TTS

**Capabilities:**
- `manage_lists` - Create and manage lists (grocery, shopping, to-do)
- `reminders` - Store and retrieve reminders
- `notes` - Save and retrieve general notes and information
- `list_management` - View, clear, and delete notes and lists

**Storage:** `~/.clarvis/notes/` (local JSON files for privacy)

**Usage:**
```python
from clarvis_agents.notes_agent import NotesAgent

agent = NotesAgent()
response = agent.handle_query("Add milk to my grocery list")
```

**API Access:**
```bash
curl -X POST http://<YOUR_HOST_IP>:8000/api/v1/query \
     -H "Content-Type: application/json" \
     -d '{"query": "add milk to my grocery list"}'
```

**Voice Examples:**
- "Add milk to my grocery list"
- "What's on my grocery list?"
- "Remind me to call the dentist"
- "Take a note: the garage code is 1234"
- "What notes do I have?"
- "Clear my shopping list"

### Agent Status

| Agent | Location | Status | Reason |
|-------|----------|--------|--------|
| Gmail Agent | Local (UN100P) | ✅ Implemented | Privacy - email content stays local |
| Ski Agent | Local (UN100P) | ✅ Implemented | Low latency, local data aggregation |
| Notes Agent | Local (UN100P) | ✅ Implemented | Privacy - notes stored locally |
| Router/Orchestrator | Local (UN100P) | ✅ Implemented | Low latency, controls routing |
| Calendar Agent | AWS Lambda | Planned | Low sensitivity, benefits from cloud |
| Weather Agent | AWS Lambda | Planned | Public data, stateless |
| Events Agent | AWS Lambda | Planned | Public data, stateless |

### MCP Server Integration

Agents use MCP (Model Context Protocol) servers for external service integration:

```python
# Gmail MCP Server configuration (from agent.py)
options = ClaudeAgentOptions(
    mcp_servers={
        "gmail": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
            "env": {...}
        }
    }
)
```

**Available MCP Servers:**
- `@gongrzhe/server-gmail-autoauth-mcp` - Gmail access with auto-auth (external, requires OAuth)

**Native SDK Tools:**
Agents can also use native Python tools via `create_sdk_mcp_server()` for simpler integrations:
- Ski Agent uses native `httpx` fetch tool for ski conditions (faster than external MCP)
- Notes Agent uses native file I/O tools for local JSON storage

---

## Security Considerations

### Local Security

- [x] Windows Firewall configured for Clarvis API (port 8000, Private+Public profiles)
- [ ] Strong passwords for HA admin account
- [ ] SSH key-based authentication (no password)
- [ ] Regular Windows and HAOS updates

### Network Security

- [x] Home Assistant behind home router NAT
- [x] Clarvis API only accessible on local network (no port forwarding)
- [ ] No port forwarding to HA (use Nabu Casa or VPN for remote access)
- [ ] mDNS limited to local network

### API Security

- [x] Gmail Agent runs in read-only mode (send/delete/modify blocked)
- [x] API keys stored in environment variables (`.env` file)
- [ ] Rotate API keys periodically
- [ ] Use least-privilege access for all integrations
- [ ] Rate limiting implemented in Gmail Agent

### Privacy Matrix

| Data Type | Sensitivity | Storage Location | Encryption |
|-----------|-------------|------------------|------------|
| Email content | High | Local only | Yes |
| Notes/lists | Medium | Local only | N/A |
| Calendar events | Medium | Cloud OK | Yes |
| Weather queries | Low | Cloud OK | N/A |
| Voice audio | Medium | Processed locally | N/A |

---

## Setup Checklist

### Phase 0: VM Setup

- [x] Verify Windows 11 Pro edition
- [x] Enable Hyper-V via PowerShell
- [x] Restart PC
- [x] Create External Virtual Switch "Home Assistant Bridge"
- [x] Download HAOS VHDX image
- [x] Create Gen 2 VM (4GB RAM, 2 CPUs)
- [x] Disable Secure Boot in VM settings
- [x] Start VM and wait for first boot
- [x] Access `http://homeassistant.local:8123`
- [x] Complete onboarding wizard
- [ ] Install Terminal & SSH add-on
- [ ] Install Samba add-on
- [x] Configure VM auto-start

### Phase 0: Voice PE Setup

- [ ] Power on Voice PE
- [ ] Connect to Wi-Fi (same network as HA)
- [ ] Discover in HA: Settings > Devices & Services
- [ ] Configure Assist pipeline
- [ ] Test wake word and basic commands

### Phase 1: API Server (✅ Complete - Issue #4)

- [x] Set up Python environment on Windows host (uv package manager)
- [x] Install Claude Agent SDK and dependencies
- [x] Build Gmail Agent with MCP integration
- [x] Create FastAPI server (`clarvis_agents/api/`)
- [x] Implement health endpoint (`GET /health`)
- [x] Implement Gmail query endpoint (`POST /api/v1/gmail/query`)
- [x] Add configuration files (`configs/api_config.json`)
- [x] Create server entry point (`scripts/run_api_server.py`)
- [x] Add comprehensive tests (`tests/test_api_server.py`)

### Phase 2: Network Configuration (✅ Complete - Issue #5)

- [x] Create Windows Firewall rule (port 8000, Private+Public profiles)
- [x] Identify Windows host IP on Home Assistant Bridge (<YOUR_HOST_IP>)
- [x] Test API connectivity from HA VM
- [x] Create network setup documentation (`docs/homeassistant_setup.md`)
- [x] Add network configuration tests (`tests/test_network_config.py`)
- [ ] Migrate from WiFi to Ethernet adapter (Issue #8)

### Phase 3: Home Assistant Integration (In Progress - Issue #6)

- [x] Create HA custom component (`custom_components/clarvis/`)
- [x] Implement conversation agent interface (`ClarvisConversationEntity`)
- [x] Add intent detection for email queries (keyword matching)
- [x] Implement config flow UI for API host/port configuration
- [x] Add comprehensive tests (`tests/test_ha_component.py`)
- [ ] Deploy component to Home Assistant
- [ ] Configure Assist pipeline to use Clarvis agent
- [ ] Test voice → agent → voice loop

### Phase 6: API Integration for Orchestrator (✅ Complete - Issue #16)

- [x] Create orchestrator endpoints (`clarvis_agents/api/routes/orchestrator.py`)
- [x] Add `POST /api/v1/query` endpoint for orchestrator queries
- [x] Add `GET /api/v1/agents` endpoint for agent discovery
- [x] Update health endpoint to show orchestrator status
- [x] Add orchestrator to API configuration (`configs/api_config.json`)
- [x] Add comprehensive tests (`tests/test_api_orchestrator.py`)
- [x] Update API documentation

### Phase 8: Orchestrator Tests (✅ Complete - Issue #18)

- [x] Reorganize tests from flat structure to nested directories
- [x] Create `tests/test_core/` directory (test_base_agent.py, test_registry.py, test_context.py)
- [x] Create `tests/test_orchestrator/` directory (test_classifier.py, test_router.py, test_orchestrator.py)
- [x] Add comprehensive edge case tests for all components
- [x] Add session continuity tests for API endpoints
- [x] Achieve 99% test coverage for core and orchestrator modules (target was >80%)
- [x] 338 unit tests passing

### Phase 9: Streaming Support (✅ Complete - Issue #19)

- [x] Add `stream()` method to `BaseAgent` abstract class with default fallback
- [x] Implement `stream()` in `GmailAgent` for real-time response streaming
- [x] Add streaming methods to `OrchestratorAgent` (`stream()`, `_stream_direct()`, `_stream_single_agent()`, `_stream_fallback()`)
- [x] Create SSE streaming endpoint `POST /api/v1/query/stream` in API routes
- [x] Update HA component with `_attr_supports_streaming = True`
- [x] Implement ChatLog integration (`_async_handle_message()`) for HA 2025.7+
- [x] Add SSE client (`_stream_from_api()`) to consume streaming API
- [x] Implement smart fallback with `HA_COMMAND_KEYWORDS` for device control
- [x] Add graceful degradation for older HA versions without ChatLog API
- [x] Update tests for streaming functionality

### Phase 10: Promptfoo Evaluation Framework (✅ Complete - Issue #39)

- [x] Create `evals/` directory structure with documentation
- [x] Implement Python test harness (`provider.py`, `run_router.py`) for promptfoo integration
- [x] Create core routing tests (`routing_eval.yaml`) - 30 tests for Gmail, Ski, Notes agents
- [x] Add edge case tests (`edge_cases.yaml`) - 20 tests for keyword conflicts, ambiguous queries
- [x] Add follow-up detection tests (`follow_up.yaml`) - 15 tests for multi-turn context
- [x] Create Makefile with `eval-routing`, `eval-edge`, `eval-follow`, `eval-all`, `eval-view` targets
- [x] 65 total evaluation tests, 100% pass rate

---

## Evaluation Framework

The `evals/` directory contains a Promptfoo-based evaluation framework for testing orchestrator routing accuracy.

### Running Evaluations

```bash
# Run all evaluations (65 tests)
make eval-all

# Run specific test suites
make eval-routing    # Core routing tests (30 tests)
make eval-edge       # Edge case tests (20 tests)
make eval-follow     # Follow-up detection tests (15 tests)

# View results in browser
make eval-view
```

### Test Categories

| Suite | Tests | Description |
|-------|-------|-------------|
| `routing_eval.yaml` | 30 | Core routing for Gmail, Ski, Notes agents and direct handling |
| `edge_cases.yaml` | 20 | Edge cases, keyword conflicts, case sensitivity |
| `follow_up.yaml` | 15 | Multi-turn conversation context and follow-up detection |

### Adding Tests for New Agents

When adding a new agent:

1. Register mock agent in `evals/provider.py`
2. Add routing tests to `evals/routing_eval.yaml`
3. Add edge cases to `evals/edge_cases.yaml` if keywords overlap
4. Run `make eval-all` to verify

See `evals/README.md` for detailed documentation.

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-31 | 1.0 | Initial architecture document |
| 2026-01-04 | 2.0 | Added Clarvis API Server section; Updated network architecture with actual IPs and firewall config; Updated agent architecture with Gmail Agent implementation; Updated setup checklist with Phase 1 & 2 completion |
| 2026-01-06 | 2.1 | Added HAOS version info (Core 2025.12.5, Supervisor 2025.12.3, OS 16.3); Updated Phase 3 progress with custom component implementation; Updated installed add-ons status |
| 2026-01-12 | 2.2 | Added orchestrator module with IntentClassifier for code-based routing (Issue #12); Added orchestrator_config.json |
| 2026-01-12 | 2.3 | Added IntentRouter with hybrid code/LLM routing (Issue #13); Added router.py and prompts.py to orchestrator module |
| 2026-01-12 | 2.4 | Added OrchestratorAgent with session management and routing coordination (Issue #14); Added agent.py with create_orchestrator factory |
| 2026-01-13 | 2.5 | GmailAgent now implements BaseAgent interface for orchestrator integration (Issue #15); Updated agent status table |
| 2026-01-13 | 2.6 | Added orchestrator API endpoints (Issue #16); Added POST /api/v1/query and GET /api/v1/agents; Updated API config and health endpoint |
| 2026-01-13 | 2.7 | Enhanced orchestrator configuration (Issue #17); Migrated to nested config structure with orchestrator/routing/agents/logging sections; Added configuration options table |
| 2026-01-13 | 2.8 | Reorganized tests into nested structure (Issue #18); Created tests/test_core/ and tests/test_orchestrator/ directories; Added comprehensive edge case tests; Achieved 99% test coverage |
| 2026-01-15 | 2.9 | Added streaming architecture (Issue #19); New SSE endpoint `/api/v1/query/stream`; Added `stream()` method to BaseAgent, OrchestratorAgent, and GmailAgent; HA component updated with ChatLog streaming support for HA 2025.7+; Smart fallback to HA default agent for device commands |
| 2026-01-16 | 2.10 | Added Ski Agent for Mt Hood Meadows conditions reporting; New `clarvis_agents/ski_agent/` module with BaseAgent implementation; Uses mcp-server-fetch for web requests; Added ski patterns to IntentClassifier; Updated orchestrator routing |
| 2026-01-16 | 2.11 | Added Notes Agent for notes, lists, and reminders; New `clarvis_agents/notes_agent/` module with BaseAgent implementation; Uses native SDK tools for local JSON file storage in `~/.clarvis/notes/`; Added notes patterns to IntentClassifier; Updated orchestrator routing |
| 2026-01-16 | 2.12 | Refactored Ski Agent to use native SDK tools instead of external mcp-server-fetch; New `clarvis_agents/ski_agent/tools.py` with httpx-based fetch; Faster startup, no subprocess overhead; Added comprehensive tests for native tools |
| 2026-01-19 | 2.13 | Added detailed agent architecture documentation (`docs/agent_architecture.md`) with ASCII diagrams showing multi-agent orchestration pattern, core abstractions, routing flow, and how to add new agents |
| 2026-01-20 | 2.14 | Added Promptfoo evaluation framework (Issue #39); New `evals/` directory with 65 routing tests; Added Makefile with eval targets; 100% pass rate on routing, edge case, and follow-up tests |
| 2026-01-21 | 2.15 | Public release preparation: Removed hardcoded IPs (replaced with `<YOUR_HOST_IP>` placeholders); Made API host configurable via CLARVIS_API_HOST env var; Removed exploratory scripts from git; Added LICENSE, CONTRIBUTING.md, SECURITY.md; Enhanced .env.example with documentation; Added type hints to __init__ methods |
