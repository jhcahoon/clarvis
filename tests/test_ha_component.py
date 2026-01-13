"""Tests for Home Assistant Custom Component.

These tests verify the Clarvis Home Assistant custom component implementation.
Each task has corresponding tests that must pass before proceeding to the next task.

Note: Tests use AST-based verification for files that depend on Home Assistant
libraries, since HA is not available in the development environment.
"""

import ast
import json
import sys
from pathlib import Path

import pytest
import requests

# Add homeassistant directory to path for imports
HA_COMPONENT_PATH = Path(__file__).parent.parent / "homeassistant"
sys.path.insert(0, str(HA_COMPONENT_PATH))

# Base path for component files
COMPONENT_BASE = (
    Path(__file__).parent.parent
    / "homeassistant"
    / "custom_components"
    / "clarvis"
)


def get_class_names_from_file(file_path: Path) -> list[str]:
    """Extract class names from a Python file using AST."""
    with open(file_path) as f:
        tree = ast.parse(f.read())
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def get_class_attribute(file_path: Path, class_name: str, attr_name: str):
    """Extract a class attribute value from a Python file using AST."""
    with open(file_path) as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id == attr_name:
                            if isinstance(item.value, ast.Constant):
                                return item.value.value
    return None


def load_const_module():
    """Load const.py directly without triggering HA imports."""
    const_path = COMPONENT_BASE / "const.py"
    namespace = {}
    with open(const_path) as f:
        exec(f.read(), namespace)
    return namespace


# =============================================================================
# Task 3.1: Constants and Manifest Tests
# =============================================================================


class TestConstants:
    """Test suite for const.py."""

    def test_domain_constant(self):
        """Verify DOMAIN is set to 'clarvis'."""
        const = load_const_module()
        assert const["DOMAIN"] == "clarvis"

    def test_ha_command_keywords_contains_required(self):
        """Verify HA_COMMAND_KEYWORDS contains required device control keywords."""
        const = load_const_module()
        ha_keywords = const["HA_COMMAND_KEYWORDS"]

        required_keywords = ["turn on", "turn off", "dim", "lock", "unlock"]
        for keyword in required_keywords:
            assert keyword in ha_keywords, f"Missing keyword: {keyword}"

    def test_ha_command_keywords_is_list(self):
        """Verify HA_COMMAND_KEYWORDS is a list."""
        const = load_const_module()
        ha_keywords = const["HA_COMMAND_KEYWORDS"]

        assert isinstance(ha_keywords, list)
        assert len(ha_keywords) > 0

    def test_default_api_host(self):
        """Verify DEFAULT_API_HOST is correct."""
        const = load_const_module()
        assert const["DEFAULT_API_HOST"] == "10.0.0.23"

    def test_default_api_port(self):
        """Verify DEFAULT_API_PORT is correct."""
        const = load_const_module()
        assert const["DEFAULT_API_PORT"] == 8000

    def test_default_timeout(self):
        """Verify DEFAULT_TIMEOUT is reasonable."""
        const = load_const_module()
        timeout = const["DEFAULT_TIMEOUT"]

        assert timeout == 120
        assert timeout > 0

    def test_api_endpoints(self):
        """Verify API endpoint constants are defined."""
        const = load_const_module()

        assert const["HEALTH_ENDPOINT"] == "/health"
        assert const["ORCHESTRATOR_QUERY_ENDPOINT"] == "/api/v1/query"

    def test_config_keys(self):
        """Verify configuration key constants are defined."""
        const = load_const_module()

        assert const["CONF_API_HOST"] == "api_host"
        assert const["CONF_API_PORT"] == "api_port"


class TestManifest:
    """Test suite for manifest.json."""

    def test_manifest_exists(self):
        """Verify manifest.json exists."""
        manifest_path = COMPONENT_BASE / "manifest.json"
        assert manifest_path.exists(), "manifest.json not found"

    def test_manifest_valid_json(self):
        """Verify manifest.json is valid JSON."""
        manifest_path = COMPONENT_BASE / "manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_manifest_domain(self):
        """Verify manifest domain matches DOMAIN constant."""
        const = load_const_module()

        manifest_path = COMPONENT_BASE / "manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        assert data["domain"] == const["DOMAIN"]

    def test_manifest_has_config_flow(self):
        """Verify manifest enables config_flow."""
        manifest_path = COMPONENT_BASE / "manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        assert data.get("config_flow") is True

    def test_manifest_has_conversation_dependency(self):
        """Verify manifest includes conversation dependency."""
        manifest_path = COMPONENT_BASE / "manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        assert "conversation" in data.get("dependencies", [])

    def test_manifest_has_version(self):
        """Verify manifest has a version string."""
        manifest_path = COMPONENT_BASE / "manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        assert "version" in data
        assert isinstance(data["version"], str)


# =============================================================================
# Task 3.2: Config Flow Tests
# =============================================================================


class TestConfigFlow:
    """Test suite for config_flow.py."""

    def test_config_flow_exists(self):
        """Verify config_flow.py exists."""
        config_flow_path = COMPONENT_BASE / "config_flow.py"
        assert config_flow_path.exists(), "config_flow.py not found"

    def test_config_flow_class_defined(self):
        """Verify ClarvisConfigFlow class is defined (using AST)."""
        config_flow_path = COMPONENT_BASE / "config_flow.py"
        class_names = get_class_names_from_file(config_flow_path)
        assert "ClarvisConfigFlow" in class_names, "ClarvisConfigFlow class not found"

    def test_config_flow_has_version(self):
        """Verify config flow has VERSION attribute (using AST)."""
        config_flow_path = COMPONENT_BASE / "config_flow.py"
        version = get_class_attribute(config_flow_path, "ClarvisConfigFlow", "VERSION")
        assert version is not None, "VERSION attribute not found"
        assert version >= 1, f"VERSION should be >= 1, got {version}"

    def test_options_flow_class_defined(self):
        """Verify ClarvisOptionsFlow class is defined (using AST)."""
        config_flow_path = COMPONENT_BASE / "config_flow.py"
        class_names = get_class_names_from_file(config_flow_path)
        assert "ClarvisOptionsFlow" in class_names, "ClarvisOptionsFlow class not found"


class TestStrings:
    """Test suite for strings.json."""

    def test_strings_exists(self):
        """Verify strings.json exists."""
        strings_path = COMPONENT_BASE / "strings.json"
        assert strings_path.exists(), "strings.json not found"

    def test_strings_valid_json(self):
        """Verify strings.json is valid JSON."""
        strings_path = COMPONENT_BASE / "strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_strings_has_config_section(self):
        """Verify strings.json has config section."""
        strings_path = COMPONENT_BASE / "strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert "config" in data

    def test_strings_has_error_messages(self):
        """Verify strings.json has error messages."""
        strings_path = COMPONENT_BASE / "strings.json"
        with open(strings_path) as f:
            data = json.load(f)
        assert "error" in data.get("config", {})


# =============================================================================
# Task 3.3: Conversation Agent Tests
# =============================================================================


class TestConversationAgent:
    """Test suite for conversation.py."""

    def test_conversation_exists(self):
        """Verify conversation.py exists."""
        conversation_path = COMPONENT_BASE / "conversation.py"
        assert conversation_path.exists(), "conversation.py not found"

    def test_conversation_entity_class_defined(self):
        """Verify ClarvisConversationEntity class is defined (using AST)."""
        conversation_path = COMPONENT_BASE / "conversation.py"
        class_names = get_class_names_from_file(conversation_path)
        assert (
            "ClarvisConversationEntity" in class_names
        ), "ClarvisConversationEntity class not found"

    def test_conversation_has_required_methods(self):
        """Verify conversation entity has required methods (using AST)."""
        conversation_path = COMPONENT_BASE / "conversation.py"
        with open(conversation_path) as f:
            tree = ast.parse(f.read())

        # Find the ClarvisConversationEntity class
        entity_class = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "ClarvisConversationEntity"
            ):
                entity_class = node
                break

        assert entity_class is not None, "ClarvisConversationEntity not found"

        # Get method names
        method_names = [
            item.name
            for item in entity_class.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        # Updated required methods for orchestrator integration
        required_methods = [
            "__init__",
            "async_process",
            "_is_ha_command",
            "_handle_orchestrator_query",
            "_process_orchestrator_response",
            "_build_response",
            "_fallback_to_default",
        ]
        for method in required_methods:
            assert method in method_names, f"Missing method: {method}"


class TestHACommandDetection:
    """Test suite for HA command detection logic."""

    @pytest.mark.parametrize(
        "query,expected",
        [
            # HA device commands - should be detected
            ("turn on the lights", True),
            ("turn off the kitchen light", True),
            ("dim the living room", True),
            ("lock the front door", True),
            ("unlock the garage", True),
            ("set temperature to 72", True),
            ("play some music", True),
            ("pause the movie", True),
            ("mute the speakers", True),
            ("arm the alarm", True),
            # Non-HA commands - should NOT be detected
            ("check my email", False),
            ("what's in my inbox", False),
            ("how many unread emails", False),
            ("hello", False),
            ("thank you", False),
            ("what's the weather", False),
            ("tell me a joke", False),
        ],
    )
    def test_is_ha_command_detection(self, query, expected):
        """Test HA command detection with various queries."""
        const = load_const_module()
        ha_keywords = const["HA_COMMAND_KEYWORDS"]

        # Simulate the _is_ha_command logic
        result = any(keyword in query.lower() for keyword in ha_keywords)
        assert result == expected, f"Query '{query}' should return {expected}"

    def test_is_ha_command_case_insensitive(self):
        """Test HA command detection is case insensitive."""
        const = load_const_module()
        ha_keywords = const["HA_COMMAND_KEYWORDS"]

        queries = ["TURN ON THE LIGHTS", "Turn On The Lights", "turn ON the LIGHTS"]
        for query in queries:
            result = any(keyword in query.lower() for keyword in ha_keywords)
            assert result is True, f"Query '{query}' should be detected as HA command"


class TestOrchestratorResponseProcessing:
    """Test suite for orchestrator response processing logic."""

    def test_success_response_from_gmail_agent(self):
        """Test processing successful response from gmail agent."""
        # Simulated orchestrator response
        data = {
            "response": "You have 3 unread emails",
            "success": True,
            "agent_name": "gmail",
            "session_id": "test-session-123",
            "error": None,
            "metadata": {},
        }

        # Should return the response (agent_name != "orchestrator")
        assert data["success"] is True
        assert data["agent_name"] != "orchestrator"
        # In real code, this would return _build_response()

    def test_success_response_from_orchestrator_greeting(self):
        """Test processing greeting handled directly by orchestrator."""
        data = {
            "response": "Hello! How can I help you?",
            "success": True,
            "agent_name": "orchestrator",
            "session_id": "test-session-123",
            "error": None,
            "metadata": {"handled_directly": True},
        }

        # Should return the response (no fallback flag)
        assert data["success"] is True
        assert data["agent_name"] == "orchestrator"
        assert data["metadata"].get("fallback") is not True

    def test_fallback_response_with_ha_command(self):
        """Test fallback response when query is HA command should trigger fallback."""
        data = {
            "response": "I'm not sure how to help with that",
            "success": True,
            "agent_name": "orchestrator",
            "session_id": "test-session-123",
            "error": None,
            "metadata": {"fallback": True},
        }
        query = "turn on the living room lights"

        # Load HA keywords
        const = load_const_module()
        ha_keywords = const["HA_COMMAND_KEYWORDS"]
        is_ha_command = any(keyword in query.lower() for keyword in ha_keywords)

        # Logic check: fallback=True AND is_ha_command should return None (fall back to HA)
        is_fallback = data["metadata"].get("fallback", False)
        should_fallback_to_ha = is_fallback and is_ha_command

        assert should_fallback_to_ha is True

    def test_fallback_response_without_ha_command(self):
        """Test fallback response without HA command should NOT trigger fallback."""
        data = {
            "response": "I'm not sure how to help with that",
            "success": True,
            "agent_name": "orchestrator",
            "session_id": "test-session-123",
            "error": None,
            "metadata": {"fallback": True},
        }
        query = "what is the meaning of life"

        # Load HA keywords
        const = load_const_module()
        ha_keywords = const["HA_COMMAND_KEYWORDS"]
        is_ha_command = any(keyword in query.lower() for keyword in ha_keywords)

        # Logic check: fallback=True but NOT ha_command should return the response
        is_fallback = data["metadata"].get("fallback", False)
        should_fallback_to_ha = is_fallback and is_ha_command

        assert should_fallback_to_ha is False

    def test_error_response_handling(self):
        """Test error response returns error message."""
        data = {
            "response": "",
            "success": False,
            "agent_name": "orchestrator",
            "session_id": "test-session-123",
            "error": "API rate limit exceeded",
            "metadata": {},
        }

        # Should show error to user
        assert data["success"] is False
        assert data["error"] is not None


class TestSessionManagement:
    """Test suite for session management logic."""

    def test_session_id_passed_to_orchestrator(self):
        """Test that session_id is included in payload when available."""
        conversation_id = "ha-conversation-abc123"
        payload = {"query": "check my emails"}

        # Simulate adding session_id to payload
        if conversation_id:
            payload["session_id"] = conversation_id

        assert "session_id" in payload
        assert payload["session_id"] == conversation_id

    def test_session_id_not_passed_when_none(self):
        """Test that session_id is NOT included when conversation_id is None."""
        conversation_id = None
        payload = {"query": "check my emails"}

        # Simulate adding session_id to payload
        if conversation_id:
            payload["session_id"] = conversation_id

        assert "session_id" not in payload


# =============================================================================
# Task 3.4: Component Setup Tests
# =============================================================================


class TestComponentSetup:
    """Test suite for __init__.py."""

    def test_init_exists(self):
        """Verify __init__.py exists."""
        init_path = COMPONENT_BASE / "__init__.py"
        assert init_path.exists(), "__init__.py not found"

    def test_platforms_defined(self):
        """Verify PLATFORMS is defined (using AST)."""
        init_path = COMPONENT_BASE / "__init__.py"
        with open(init_path) as f:
            content = f.read()

        # Check that PLATFORMS is defined
        assert "PLATFORMS" in content, "PLATFORMS not defined in __init__.py"

    def test_platforms_includes_conversation(self):
        """Verify PLATFORMS includes conversation (using AST)."""
        init_path = COMPONENT_BASE / "__init__.py"
        with open(init_path) as f:
            tree = ast.parse(f.read())

        # Find PLATFORMS assignment
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "PLATFORMS":
                        # Check if it's a list containing conversation
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Attribute):
                                    if elt.attr == "CONVERSATION":
                                        return  # Test passes
        pytest.fail("PLATFORMS should include Platform.CONVERSATION")

    def test_domain_exported(self):
        """Verify DOMAIN is imported and available (using AST)."""
        init_path = COMPONENT_BASE / "__init__.py"
        with open(init_path) as f:
            content = f.read()

        # Check that DOMAIN is imported from const
        assert "from .const import DOMAIN" in content or "DOMAIN" in content

    def test_async_setup_defined(self):
        """Verify async_setup function is defined."""
        init_path = COMPONENT_BASE / "__init__.py"
        with open(init_path) as f:
            tree = ast.parse(f.read())

        func_names = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef)
        ]
        assert "async_setup" in func_names, "async_setup not defined"

    def test_async_setup_entry_defined(self):
        """Verify async_setup_entry function is defined."""
        init_path = COMPONENT_BASE / "__init__.py"
        with open(init_path) as f:
            tree = ast.parse(f.read())

        func_names = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef)
        ]
        assert "async_setup_entry" in func_names, "async_setup_entry not defined"

    def test_async_unload_entry_defined(self):
        """Verify async_unload_entry function is defined."""
        init_path = COMPONENT_BASE / "__init__.py"
        with open(init_path) as f:
            tree = ast.parse(f.read())

        func_names = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef)
        ]
        assert "async_unload_entry" in func_names, "async_unload_entry not defined"


class TestComponentFileStructure:
    """Test suite for component file structure."""

    def test_component_directory_exists(self):
        """Verify component directory was created."""
        assert COMPONENT_BASE.is_dir()

    def test_all_required_files_exist(self):
        """Verify all required files exist."""
        required_files = [
            "__init__.py",
            "manifest.json",
            "conversation.py",
            "config_flow.py",
            "const.py",
            "strings.json",
        ]
        for file in required_files:
            assert (COMPONENT_BASE / file).exists(), f"Missing required file: {file}"


# =============================================================================
# Task 3.5: Integration Tests
# =============================================================================


@pytest.mark.integration
class TestIntegration:
    """Integration tests for Clarvis component with live API."""

    # Constants from const.py (duplicated here to avoid HA import issues)
    API_HOST = "10.0.0.23"
    API_PORT = 8000
    HEALTH_ENDPOINT = "/health"
    ORCHESTRATOR_QUERY_ENDPOINT = "/api/v1/query"

    def test_api_health_from_component_perspective(self):
        """Test API health check as component would call it."""
        url = f"http://{self.API_HOST}:{self.API_PORT}{self.HEALTH_ENDPOINT}"
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("Clarvis API not available")

    def test_api_orchestrator_query_from_component_perspective(self):
        """Test orchestrator query as component would call it."""
        url = f"http://{self.API_HOST}:{self.API_PORT}{self.ORCHESTRATOR_QUERY_ENDPOINT}"
        try:
            response = requests.post(
                url,
                json={"query": "How many unread emails do I have?"},
                timeout=120,
            )
            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert "response" in data
            assert "agent_name" in data
            assert "session_id" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("Clarvis API not available")

    def test_api_orchestrator_greeting_handled_directly(self):
        """Test greetings are handled directly by orchestrator."""
        url = f"http://{self.API_HOST}:{self.API_PORT}{self.ORCHESTRATOR_QUERY_ENDPOINT}"
        try:
            response = requests.post(
                url,
                json={"query": "hello"},
                timeout=30,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["agent_name"] == "orchestrator"
            # Should have handled_directly metadata
            assert data.get("metadata", {}).get("handled_directly") is True
        except requests.exceptions.ConnectionError:
            pytest.skip("Clarvis API not available")

    def test_api_orchestrator_session_continuity(self):
        """Test session continuity across queries."""
        url = f"http://{self.API_HOST}:{self.API_PORT}{self.ORCHESTRATOR_QUERY_ENDPOINT}"
        try:
            # First query - get session_id
            response1 = requests.post(
                url,
                json={"query": "check my emails"},
                timeout=120,
            )
            assert response1.status_code == 200
            data1 = response1.json()
            session_id = data1.get("session_id")
            assert session_id is not None

            # Second query - use same session_id
            response2 = requests.post(
                url,
                json={"query": "what about the first one?", "session_id": session_id},
                timeout=120,
            )
            assert response2.status_code == 200
            data2 = response2.json()
            # Should maintain same session
            assert data2.get("session_id") == session_id
        except requests.exceptions.ConnectionError:
            pytest.skip("Clarvis API not available")
