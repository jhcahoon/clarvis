# AI Home Assistant - Technical Architecture

**Last Updated:** January 4, 2026

---

## Table of Contents
1. [Infrastructure Overview](#infrastructure-overview)
2. [Local Infrastructure](#local-infrastructure)
3. [Clarvis API Server](#clarvis-api-server)
4. [Network Architecture](#network-architecture)
5. [Cloud Infrastructure](#cloud-infrastructure-future)
6. [Agent Architecture](#agent-architecture)
7. [Security Considerations](#security-considerations)

---

## Infrastructure Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Home Network                              │
│                                                                  │
│  ┌──────────────────────────────────────────┐                   │
│  │     MINISFORUM UN100P (Windows 11 Pro)   │                   │
│  │                                          │                   │
│  │  ┌────────────────────────────────────┐  │                   │
│  │  │   Hyper-V VM: Home Assistant OS    │  │                   │
│  │  │   - Supervisor                     │  │                   │
│  │  │   - Add-ons (SSH, Samba, etc.)     │  │                   │
│  │  │   - Custom Integrations            │  │                   │
│  │  └──────────────┬─────────────────────┘  │                   │
│  │                 │ HTTP :8000             │                   │
│  │                 ▼                        │                   │
│  │  ┌────────────────────────────────────┐  │                   │
│  │  │   Windows Host (10.0.0.23)         │  │                   │
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

### Host Machine: MINISFORUM UN100P

| Spec | Value |
|------|-------|
| CPU | Intel N100 (4 cores, 4 threads, up to 3.4GHz) |
| RAM | 16 GB DDR4 |
| Storage | 256 GB NVMe SSD |
| OS | Windows 11 Pro |
| Network | Gigabit Ethernet + Wi-Fi 6 |

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
Wake Word → STT (Whisper) → Intent → Agent → Response → TTS (Piper) → Audio
    │            │                      │                    │
    └── Device ──┴──── Home Assistant ──┴──── Home Assistant ┘
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
│       └── health.py       # GET /health
├── gmail_agent/
│   ├── __init__.py
│   ├── config.py           # GmailAgentConfig, RateLimiter
│   ├── prompts.py          # System prompts
│   └── tools.py            # Helper tools
configs/
├── api_config.json         # API server configuration
├── gmail_agent_config.json # Gmail agent settings
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
| `/api/v1/gmail/query` | POST | Query the Gmail agent with natural language |

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
    }
  }
}
```

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
    │10.0.0.23│   │  (DHCP)  │   │  (DHCP)  │
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
- **Windows Host:** Access via IP `10.0.0.23` (mDNS not available)
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

### Current Implementation

The Gmail Agent is fully implemented and accessible via the Clarvis API Server.

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

**Features:**
- Natural language email queries via Claude Agent SDK
- MCP (Model Context Protocol) integration for Gmail access
- Read-only mode for safety (blocks send/delete/modify operations)
- Rate limiting via sliding window algorithm
- OAuth authentication via `~/.gmail-mcp/` credentials

**Usage:**
```python
from clarvis_agents.gmail_agent import GmailAgent

agent = GmailAgent(read_only=True)
response = agent.check_emails("How many unread emails do I have?")
```

**API Access:**
```bash
curl -X POST http://10.0.0.23:8000/api/v1/gmail/query \
     -H "Content-Type: application/json" \
     -d '{"query": "check my unread emails"}'
```

### Future Agents (Planned)

| Agent | Location | Status | Reason |
|-------|----------|--------|--------|
| Gmail Agent | Local (UN100P) | ✅ Implemented | Privacy - email content stays local |
| Calendar Agent | AWS Lambda | Planned | Low sensitivity, benefits from cloud |
| Weather Agent | AWS Lambda | Planned | Public data, stateless |
| Events Agent | AWS Lambda | Planned | Public data, stateless |
| Router/Orchestrator | Local (UN100P) | Planned | Low latency, controls routing |

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
- `@gongrzhe/server-gmail-autoauth-mcp` - Gmail access with auto-auth

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
- [x] Identify Windows host IP on Home Assistant Bridge (10.0.0.23)
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

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-31 | 1.0 | Initial architecture document |
| 2026-01-04 | 2.0 | Added Clarvis API Server section; Updated network architecture with actual IPs and firewall config; Updated agent architecture with Gmail Agent implementation; Updated setup checklist with Phase 1 & 2 completion |
| 2026-01-06 | 2.1 | Added HAOS version info (Core 2025.12.5, Supervisor 2025.12.3, OS 16.3); Updated Phase 3 progress with custom component implementation; Updated installed add-ons status |
