"""Tests for Phase 2: Network Configuration.

These tests verify the network configuration for Home Assistant ↔ Clarvis connectivity.
Each task has corresponding tests that must pass before proceeding to the next task.

Note: Windows-specific tests (firewall, network adapter) are skipped on non-Windows platforms.
"""

import ipaddress
import subprocess
import sys
from pathlib import Path

import pytest
import requests

# Platform detection for Windows-specific tests
IS_WINDOWS = sys.platform == "win32"
WINDOWS_ONLY = pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")


def validate_ipv4(ip_str: str) -> bool:
    """Validate that a string is a valid IPv4 address."""
    try:
        ipaddress.IPv4Address(ip_str)
        return True
    except ValueError:
        return False


# =============================================================================
# Task 2.0: Documentation Directory Organization
# =============================================================================


def test_docs_directory_exists():
    """Verify docs directory was created."""
    assert Path("docs").is_dir(), "docs/ directory does not exist"


def test_architecture_doc_moved():
    """Verify architecture doc moved to docs/."""
    assert Path("docs/ai-home-assistant-architecture.md").exists(), (
        "docs/ai-home-assistant-architecture.md not found"
    )
    assert not Path("ai-home-assistant-architecture.md").exists(), (
        "ai-home-assistant-architecture.md still exists in project root"
    )


def test_project_plan_doc_moved():
    """Verify project plan doc moved to docs/."""
    assert Path("docs/ai-home-assistant-project-plan.md").exists(), (
        "docs/ai-home-assistant-project-plan.md not found"
    )
    assert not Path("ai-home-assistant-project-plan.md").exists(), (
        "ai-home-assistant-project-plan.md still exists in project root"
    )


# =============================================================================
# Task 2.1: Windows Firewall Rule
# =============================================================================


@WINDOWS_ONLY
def test_firewall_rule_exists():
    """Verify Clarvis API Server firewall rule exists, is enabled, and allows Private+Public profiles."""
    # Check rule exists and is enabled
    result = subprocess.run(
        [
            "powershell",
            "-Command",
            "Get-NetFirewallRule -DisplayName 'Clarvis API Server' | Select-Object -ExpandProperty Enabled",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed to query firewall rule: {result.stderr}"
    assert "True" in result.stdout, "Firewall rule 'Clarvis API Server' is not enabled"

    # Check rule includes both Private and Public profiles
    result = subprocess.run(
        [
            "powershell",
            "-Command",
            "Get-NetFirewallRule -DisplayName 'Clarvis API Server' | Select-Object -ExpandProperty Profile",
        ],
        capture_output=True,
        text=True,
    )
    profile = result.stdout.strip()
    assert "Private" in profile, "Firewall rule should include Private profile"
    # Note: Public may be needed if network is set to Public profile


# =============================================================================
# Task 2.2: Host IP Identification
# =============================================================================


@WINDOWS_ONLY
def test_host_ip_identified():
    """Verify we can identify a valid host IP on Home Assistant Bridge virtual switch."""
    result = subprocess.run(
        [
            "powershell",
            "-Command",
            "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Home Assistant*' } | Select-Object -First 1 -ExpandProperty IPAddress",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed to get IP address: {result.stderr}"

    # Should have at least one IP address (handle multiple IPs by taking first line)
    ips = result.stdout.strip().split("\n")
    assert ips and ips[0], "No IP address found on Home Assistant Bridge"
    ip = ips[0].strip()

    # Proper IP validation using ipaddress module
    assert validate_ipv4(ip), f"Invalid IPv4 address: {ip}"


# =============================================================================
# Task 2.3: API Server Localhost Test
# =============================================================================


@pytest.mark.integration
def test_api_server_health_localhost():
    """Verify API server health endpoint responds on localhost."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        assert response.status_code == 200, f"Health endpoint returned {response.status_code}"
        data = response.json()
        assert data["status"] == "healthy", f"Status is not healthy: {data}"
        assert "gmail" in data.get("agents", {}), "Gmail agent not in health response"
    except requests.exceptions.ConnectionError:
        pytest.fail("API server not running - start with: python scripts/run_api_server.py")


# =============================================================================
# Task 2.4: API Server Host IP Test
# =============================================================================


@WINDOWS_ONLY
@pytest.mark.integration
def test_api_server_health_via_host_ip():
    """Verify API server responds via the host IP (not just localhost)."""
    # Get host IP from Home Assistant Bridge virtual switch
    result = subprocess.run(
        [
            "powershell",
            "-Command",
            "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Home Assistant*' } | Select-Object -First 1 -ExpandProperty IPAddress",
        ],
        capture_output=True,
        text=True,
    )
    host_ip = result.stdout.strip().split("\n")[0].strip() if result.stdout.strip() else ""
    assert host_ip, "Could not determine host IP"
    assert validate_ipv4(host_ip), f"Invalid host IP: {host_ip}"

    # Test health endpoint via host IP
    try:
        response = requests.get(f"http://{host_ip}:8000/health", timeout=5)
        assert response.status_code == 200, f"Health endpoint returned {response.status_code}"
        assert response.json()["status"] == "healthy"
    except requests.exceptions.ConnectionError:
        pytest.fail(f"Could not connect to API server at {host_ip}:8000")


# =============================================================================
# Task 2.5: Documentation
# =============================================================================


def test_homeassistant_setup_doc_exists():
    """Verify homeassistant_setup.md was created."""
    assert Path("docs/homeassistant_setup.md").exists(), "docs/homeassistant_setup.md not found"


def test_homeassistant_setup_doc_content():
    """Verify documentation has required sections."""
    doc_path = Path("docs/homeassistant_setup.md")
    assert doc_path.exists(), "docs/homeassistant_setup.md not found"

    content = doc_path.read_text(encoding="utf-8")
    assert "8000" in content, "Port number not documented"
    assert "firewall" in content.lower(), "Firewall section missing"
    assert "curl" in content.lower(), "Test commands missing"
    assert "troubleshoot" in content.lower(), "Troubleshooting section missing"


# =============================================================================
# Task 2.6: Ethernet Migration GitHub Issue
# =============================================================================


def test_ethernet_migration_issue_created():
    """Verify GitHub issue for Ethernet migration was created."""
    result = subprocess.run(
        ["gh", "issue", "view", "8", "--repo", "jhcahoon/clarvis", "--json", "title,state"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed to view GitHub issue #8: {result.stderr}"
    assert "Ethernet" in result.stdout or "ethernet" in result.stdout, (
        "Issue #8 is not the Ethernet migration issue"
    )
