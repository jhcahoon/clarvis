# Home Assistant Integration Troubleshooting

**Started:** January 6, 2026
**Status:** In Progress
**HA Version:** Core 2025.12.5, Supervisor 2025.12.3, OS 16.3

---

## Problem Statement

The Clarvis custom component exists in the local dev repo (`homeassistant/custom_components/clarvis/`) but is not appearing in Home Assistant's integrations list when searching for it.

---

## Investigation Checklist

### Step 1: Fix Missing translations/ Folder
- [x] Create `translations/en.json` (copy from `strings.json`)
- [x] Verify file is valid JSON

**Finding:** Component has `strings.json` but NO `translations/` folder. Per [HA Developer Docs](https://developers.home-assistant.io/docs/internationalization/core/), the correct structure requires:
```
homeassistant/custom_components/clarvis/
├── strings.json           # Source file (for development)
├── translations/          # REQUIRED folder
│   └── en.json            # Copy of strings.json for runtime
```

**File to create:** `homeassistant/custom_components/clarvis/translations/en.json`

---

### Step 2: Verify Component Deployment via Samba
- [x] Check if files exist at `\\10.0.0.219\config\custom_components\clarvis\`
- [x] Verify all required files are present:
  - [x] `__init__.py`
  - [x] `manifest.json`
  - [x] `config_flow.py`
  - [x] `conversation.py`
  - [x] `const.py`
  - [x] `strings.json`
  - [x] `translations/en.json` (DEPLOYED 2026-01-06)

**Finding:** `translations/` folder was missing. Created and deployed via Samba.

---

### Step 3: Restart Home Assistant
- [ ] Go to HA web UI: `http://homeassistant.local:8123`
- [ ] Navigate to: **Settings** > **System** > **Restart**
- [ ] Wait for HA to fully restart (1-2 minutes)

---

### Step 4: Check HA Logs for Errors
- [ ] Check logs for "clarvis" mentions

**Via HA Console (Hyper-V Manager):**
```bash
# Login first, then run:
ha core logs | grep -i clarvis
```

**Via HA Web UI:**
1. **Settings** > **System** > **Logs**
2. Search for "clarvis" or filter by "Error"

**Common errors to look for:**
- `Unable to prepare setup for clarvis` - manifest issue
- `No module named` - missing file or import error
- `Invalid config` - config flow issue

**Log output:**
```
(paste log output here)
```

---

### Step 5: Verify API Server is Running
- [ ] Check if API server is running on Windows host (10.0.0.23:8000)

**On Windows host, run:**
```powershell
# Check if process is running
Get-Process python* | Where-Object {$_.CommandLine -like '*run_api_server*'}

# Or start the server
cd C:\Users\james\projects\clarvis
python scripts/run_api_server.py
```

**Test health endpoint:**
```powershell
curl http://localhost:8000/health
```

**Expected response:** `{"status":"healthy","version":"1.0.0","agents":{"gmail":"available"}}`

**Actual response:**
```
(paste response here)
```

---

### Step 6: Test API Connectivity from HA
- [ ] Test connectivity from HA VM to Windows host

**Via HA Console:**
```bash
curl http://10.0.0.23:8000/health
```

**If fails, check Windows Firewall:**
```powershell
Get-NetFirewallRule -DisplayName 'Clarvis API Server' | Select-Object Enabled, Profile
```

**Result:**
```
(paste result here)
```

---

### Step 7: Try Adding Integration via UI
- [ ] Go to: **Settings** > **Devices & Services**
- [ ] Click: **+ Add Integration**
- [ ] Search for: "Clarvis"

**If found, configure with:**
- API Host: `10.0.0.23`
- API Port: `8000`

**Result:**
- [ ] Integration appeared in search
- [ ] Configuration completed successfully
- [ ] Integration shows in Devices & Services

---

## Potential Fixes (If Steps Above Don't Work)

### Fix A: Add Manifest Version Constraint

The current `manifest.json` lacks a minimum version. Add:

```json
{
  "domain": "clarvis",
  "name": "Clarvis AI Assistant",
  "version": "1.0.0",
  "homeassistant": "2024.1.0",
  ...
}
```

**File:** `homeassistant/custom_components/clarvis/manifest.json`

---

### Fix B: Verify Config Flow Registration

Ensure `config_flow.py` has:
```python
from homeassistant.config_entries import ConfigFlow
...
class ClarvisConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
```

---

## Critical Files

| File | Location | Purpose |
|------|----------|---------|
| `manifest.json` | `homeassistant/custom_components/clarvis/` | Component metadata |
| `__init__.py` | `homeassistant/custom_components/clarvis/` | Setup entry points |
| `config_flow.py` | `homeassistant/custom_components/clarvis/` | UI configuration |
| `conversation.py` | `homeassistant/custom_components/clarvis/` | Conversation agent |
| `translations/en.json` | `homeassistant/custom_components/clarvis/translations/` | UI translations |

---

## Success Criteria

- [x] Clarvis appears in "Add Integration" search
- [x] Config flow connects to API (health check passes)
- [x] Integration shows as configured in Devices & Services
- [ ] Voice query routes through Clarvis agent

## Resolution

**Root Cause:** Two issues were discovered:
1. The `translations/` folder was missing from the component
2. Files were deployed to the wrong path (`/mnt/data/supervisor/homeassistant/`) instead of the correct path (`/config/`) accessible from the SSH add-on container

**Solution:**
- Created `translations/en.json` file
- Deployed all component files to `/config/custom_components/clarvis/` via SSH
- Restarted Home Assistant

**Key Learning:** In HAOS, the SSH add-on runs in a container with different mount points. The correct path for custom components is `/config/custom_components/` (not `/mnt/data/supervisor/homeassistant/`).

---

## Investigation Log

### 2026-01-06: Initial Analysis
- Explored component structure, found all files present except `translations/` folder
- Confirmed HA version: 2025.12.5
- Identified missing translations folder as likely root cause

### 2026-01-06: Samba Share Investigation
- Discovered Samba share at `\\10.0.0.219\config` wasn't pointing to the correct location
- Files uploaded via Samba were going to an overlay filesystem, not the actual HA config

### 2026-01-06: SSH Deployment (RESOLVED)
- Connected via SSH (`ssh -o MACs=hmac-sha2-256-etm@openssh.com root@10.0.0.219`)
- Discovered correct path is `/config/` (not `/mnt/data/supervisor/homeassistant/`)
- Created all component files manually via echo commands
- Restarted HA - integration now appears and configures successfully
- Created troubleshooting plan

---

## Sources

- [Integration manifest | Home Assistant Developer Docs](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Backend localization | Home Assistant Developer Docs](https://developers.home-assistant.io/docs/internationalization/core/)
- [Building a Home Assistant Custom Component Part 3: Config Flow](https://aarongodfrey.dev/home%20automation/building_a_home_assistant_custom_component_part_3/)
- [How translations for custom_components works](https://community.home-assistant.io/t/how-translations-for-custom-components-hacs-works/546494)
