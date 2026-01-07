"""Tests for Phase 3: Home Assistant Custom Component.

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

    def test_email_keywords_contains_required(self):
        """Verify EMAIL_KEYWORDS contains all required keywords."""
        const = load_const_module()
        email_keywords = const["EMAIL_KEYWORDS"]

        required_keywords = ["email", "inbox", "gmail", "unread"]
        for keyword in required_keywords:
            assert keyword in email_keywords, f"Missing keyword: {keyword}"

    def test_email_keywords_is_list(self):
        """Verify EMAIL_KEYWORDS is a list."""
        const = load_const_module()
        email_keywords = const["EMAIL_KEYWORDS"]

        assert isinstance(email_keywords, list)
        assert len(email_keywords) > 0

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
        assert const["GMAIL_QUERY_ENDPOINT"] == "/api/v1/gmail/query"

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

        required_methods = [
            "__init__",
            "async_process",
            "_is_email_query",
            "_handle_email_query",
            "_fallback_to_default",
        ]
        for method in required_methods:
            assert method in method_names, f"Missing method: {method}"


class TestIntentDetection:
    """Test suite for intent detection logic."""

    @pytest.mark.parametrize(
        "query,expected",
        [
            ("check my email", True),
            ("do I have any unread emails", True),
            ("what's in my inbox", True),
            ("check gmail", True),
            ("any new messages", True),
            ("read my mail", True),
            ("check my mailbox", True),
            ("what's the weather", False),
            ("turn on the lights", False),
            ("set a timer", False),
            ("play some music", False),
        ],
    )
    def test_is_email_query_detection(self, query, expected):
        """Test intent detection with various queries."""
        const = load_const_module()
        email_keywords = const["EMAIL_KEYWORDS"]

        # Simulate the _is_email_query logic
        result = any(keyword in query.lower() for keyword in email_keywords)
        assert result == expected, f"Query '{query}' should return {expected}"

    def test_is_email_query_case_insensitive(self):
        """Test intent detection is case insensitive."""
        const = load_const_module()
        email_keywords = const["EMAIL_KEYWORDS"]

        queries = ["CHECK MY EMAIL", "Check My Email", "check my EMAIL"]
        for query in queries:
            result = any(keyword in query.lower() for keyword in email_keywords)
            assert result is True, f"Query '{query}' should be detected as email query"


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
    GMAIL_QUERY_ENDPOINT = "/api/v1/gmail/query"

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

    def test_api_gmail_query_from_component_perspective(self):
        """Test Gmail query as component would call it."""
        url = f"http://{self.API_HOST}:{self.API_PORT}{self.GMAIL_QUERY_ENDPOINT}"
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
        except requests.exceptions.ConnectionError:
            pytest.skip("Clarvis API not available")
