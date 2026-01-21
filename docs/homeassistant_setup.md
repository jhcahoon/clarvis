# Home Assistant ↔ Clarvis API Setup Guide

This document describes how to configure network connectivity between Home Assistant (running in Hyper-V) and the Clarvis API server (running on the Windows host).

## Network Overview

```
┌─────────────────────────────┐     HTTP (port 8000)     ┌─────────────────────────────┐
│  Home Assistant OS          │  ─────────────────────►  │  Windows Host               │
│  (Hyper-V VM)               │                          │  Clarvis API Server         │
│                             │  ◄─────────────────────  │  (FastAPI + GmailAgent)     │
│  IP: Assigned by DHCP       │     JSON Response        │  IP: <YOUR_HOST_IP>              │
└─────────────────────────────┘                          └─────────────────────────────┘
           │                                                        │
           └────────────── Home Assistant Bridge ───────────────────┘
                          (Hyper-V Virtual Switch)
```

## Windows Host Configuration

### Host IP Address

The Windows host IP on the Home Assistant Bridge virtual switch:
- **IP Address:** `<YOUR_HOST_IP>`
- **Port:** `8000`

To verify the host IP:
```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Home Assistant*' } | Select-Object IPAddress
```

### Firewall Rule

A Windows Firewall rule named "Clarvis API Server" allows inbound TCP traffic on port 8000:

```powershell
# View the firewall rule
Get-NetFirewallRule -DisplayName 'Clarvis API Server'

# Create the rule (if not exists, run as Administrator)
# Note: Both Private and Public profiles are needed since the virtual switch may be on either
New-NetFirewallRule -DisplayName 'Clarvis API Server' `
    -Direction Inbound -Protocol TCP -LocalPort 8000 `
    -Action Allow -Profile Private,Public

# If you already created the rule with only Private, update it:
Set-NetFirewallRule -DisplayName 'Clarvis API Server' -Profile Private,Public
```

**Important:** Check which network profile your virtual switch is using:
```powershell
Get-NetConnectionProfile | Select-Object InterfaceAlias, NetworkCategory
```
If "Home Assistant Bridge" shows "Public", the firewall rule must include the Public profile.

### Starting the API Server

From the Clarvis project directory:

```bash
# Standard startup
python scripts/run_api_server.py

# Custom port
python scripts/run_api_server.py --port 8080

# Development mode with auto-reload
python scripts/run_api_server.py --reload
```

## Testing Connectivity from Home Assistant

Access the HA console via Hyper-V Manager: Right-click VM → Connect

### Health Check

```bash
curl http://<YOUR_HOST_IP>:8000/health
```

Expected response:
```json
{"status":"healthy","version":"1.0.0","agents":{"gmail":"available"}}
```

### Gmail Query Test

```bash
curl -X POST http://<YOUR_HOST_IP>:8000/api/v1/gmail/query \
     -H "Content-Type: application/json" \
     -d '{"query": "how many unread emails do I have"}'
```

Expected response:
```json
{"response":"You have X unread emails...","success":true}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check, returns server status and available agents |
| `/` | GET | Root endpoint with API info and link to docs |
| `/docs` | GET | Swagger UI documentation |
| `/api/v1/gmail/query` | POST | Query the Gmail agent with natural language |

## Troubleshooting

### Cannot connect to API server

1. **Verify API server is running on Windows host:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check Windows Firewall rule exists and is enabled:**
   ```powershell
   Get-NetFirewallRule -DisplayName 'Clarvis API Server' | Select-Object Enabled
   ```

3. **Verify both HA VM and Windows host are on the same subnet:**
   - HA VM should get an IP in the `10.0.0.x` range
   - Windows host is at `<YOUR_HOST_IP>`

4. **Check Hyper-V virtual switch configuration:**
   ```powershell
   Get-VMSwitch | Select-Object Name, SwitchType
   ```
   The "Home Assistant Bridge" should be an External switch type.

5. **Temporarily disable Windows Firewall to isolate the issue:**
   ```powershell
   # Disable (for testing only)
   Set-NetFirewallProfile -Profile Private -Enabled False

   # Re-enable after testing
   Set-NetFirewallProfile -Profile Private -Enabled True
   ```

### API server starts but Gmail agent fails

1. Check Gmail OAuth credentials are configured in `~/.gmail-mcp/`
2. Verify the MCP server can start: `npx -y @gongrzhe/server-gmail-autoauth-mcp`
3. Check API server logs for error messages

### Slow responses

- Gmail agent queries may take 10-30 seconds due to MCP server startup
- First query after server start is typically slower
- Consider implementing connection pooling for production use

## Network Adapter Note

Currently using **WiFi adapter** for the Hyper-V External Switch. A future migration to Ethernet adapter is planned for improved reliability. See GitHub issue for details.
