# AI Home Assistant - Technical Architecture

**Last Updated:** December 31, 2024

---

## Table of Contents
1. [Infrastructure Overview](#infrastructure-overview)
2. [Local Infrastructure](#local-infrastructure)
3. [Network Architecture](#network-architecture)
4. [Cloud Infrastructure](#cloud-infrastructure-future)
5. [Agent Architecture](#agent-architecture-future)
6. [Security Considerations](#security-considerations)

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
│  │  └────────────────────────────────────┘  │                   │
│  │                                          │                   │
│  │  Windows Host:                           │                   │
│  │  - Development environment               │                   │
│  │  - MCP servers                           │                   │
│  │  - Local agent execution                 │                   │
│  └──────────────────────────────────────────┘                   │
│                          │                                       │
│                    Bridged Network                               │
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

**Version:** Latest stable (auto-updates enabled)

**Core Components:**
- Home Assistant Core - main automation platform
- Supervisor - manages add-ons and system
- Operating System - minimal Linux base

**Installed Add-ons:**
- [ ] Terminal & SSH - CLI access
- [ ] Samba share - Windows file access at `\\homeassistant\config`
- [ ] File Editor - in-browser config editing
- [ ] Studio Code Server - VS Code in browser (optional)

**Custom Integrations (Planned):**
- Claude conversation agent
- Custom intent handlers for agent routing

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

## Network Architecture

### Network Topology

```
Internet
    │
    ▼
┌─────────────────────────────────────────┐
│            Home Router                   │
│         (DHCP Server)                    │
│         Subnet: 192.168.x.0/24          │
└─────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    ┌─────────┐   ┌──────────┐   ┌──────────┐
    │ Windows │   │   HAOS   │   │ Voice PE │
    │  Host   │   │    VM    │   │          │
    │ .100    │   │  .101    │   │  .102    │
    └─────────┘   └──────────┘   └──────────┘
```

### Hyper-V Virtual Switch Configuration

**Switch Name:** `Home Assistant Bridge`
**Type:** External
**Binding:** Physical network adapter (Ethernet preferred)
**Sharing:** Management OS shares adapter

This configuration gives the VM its own IP address on the home network, allowing:
- Voice PE to communicate directly with Home Assistant
- mDNS discovery (`homeassistant.local`)
- Access from any device on the network

### Ports & Protocols

| Service | Port | Protocol | Direction |
|---------|------|----------|-----------|
| Home Assistant Web UI | 8123 | HTTP/HTTPS | Inbound |
| SSH (if enabled) | 22 | TCP | Inbound |
| Samba | 445 | TCP | Inbound |
| mDNS | 5353 | UDP | Both |
| Wyoming (Voice) | 10400 | TCP | Internal |

### DNS/Discovery

- **mDNS:** Home Assistant advertises as `homeassistant.local`
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

## Agent Architecture (Future)

### Agent Communication Flow

```
┌──────────────┐     ┌───────────────────┐     ┌─────────────────┐
│  Voice PE    │────▶│  Home Assistant   │────▶│  Agent Router   │
│              │     │  (Intent Parse)   │     │  (Local)        │
└──────────────┘     └───────────────────┘     └─────────────────┘
                                                       │
                     ┌─────────────────────────────────┼─────────┐
                     │                                 │         │
                     ▼                                 ▼         ▼
              ┌─────────────┐                  ┌───────────┐ ┌───────┐
              │ Email Agent │                  │ Calendar  │ │Weather│
              │  (Local)    │                  │  (AWS)    │ │ (AWS) │
              └─────────────┘                  └───────────┘ └───────┘
```

### Base Agent Interface (Planned)

```python
from abc import ABC, abstractmethod
from anthropic import Anthropic

class BaseAgent(ABC):
    def __init__(self, client: Anthropic):
        self.client = client

    @abstractmethod
    async def process_query(self, user_input: str, context: dict) -> str:
        """Process a natural language query and return response."""
        pass

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """Return list of capabilities for routing."""
        pass
```

---

## Security Considerations

### Local Security

- [ ] Windows Firewall configured for Hyper-V
- [ ] Strong passwords for HA admin account
- [ ] SSH key-based authentication (no password)
- [ ] Regular Windows and HAOS updates

### Network Security

- [ ] Home Assistant behind home router NAT
- [ ] No port forwarding to HA (use Nabu Casa or VPN for remote access)
- [ ] mDNS limited to local network

### API Security

- [ ] API keys stored in environment variables or Secrets Manager
- [ ] Rotate API keys periodically
- [ ] Use least-privilege access for all integrations

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

- [ ] Verify Windows 11 Pro edition
- [ ] Enable Hyper-V via PowerShell
- [ ] Restart PC
- [ ] Create External Virtual Switch "Home Assistant Bridge"
- [ ] Download HAOS VHDX image
- [ ] Create Gen 2 VM (4GB RAM, 2 CPUs)
- [ ] Disable Secure Boot in VM settings
- [ ] Start VM and wait for first boot
- [ ] Access `http://homeassistant.local:8123`
- [ ] Complete onboarding wizard
- [ ] Install Terminal & SSH add-on
- [ ] Install Samba add-on
- [ ] Configure VM auto-start

### Phase 0: Voice PE Setup

- [ ] Power on Voice PE
- [ ] Connect to Wi-Fi (same network as HA)
- [ ] Discover in HA: Settings > Devices & Services
- [ ] Configure Assist pipeline
- [ ] Test wake word and basic commands

### Phase 1: Local Development

- [ ] Set up Python environment on Windows host
- [ ] Install Anthropic SDK
- [ ] Build first test agent
- [ ] Create HA custom integration
- [ ] Test voice → agent → voice loop

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-31 | 1.0 | Initial architecture document |
