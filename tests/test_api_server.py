"""Tests for Clarvis API Server (Phase 1)."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile

from fastapi.testclient import TestClient

from clarvis_agents.api.server import create_app, app
from clarvis_agents.api.config import (
    APIConfig,
    ServerConfig,
    AgentConfig,
    load_config,
)
from clarvis_agents.api.routes.gmail import GmailQueryRequest, GmailQueryResponse


class TestAPIConfig:
    """Test suite for API configuration."""

    def test_server_config_defaults(self):
        """Test ServerConfig default values."""
        config = ServerConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.cors_origins == ["*"]
        assert config.debug is False

    def test_agent_config_defaults(self):
        """Test AgentConfig default values."""
        config = AgentConfig()
        assert config.enabled is True
        assert config.timeout_seconds == 120

    def test_api_config_defaults(self):
        """Test APIConfig default values."""
        config = APIConfig()
        assert isinstance(config.server, ServerConfig)
        assert config.agents == {}

    def test_api_config_from_file(self):
        """Test loading APIConfig from a JSON file."""
        config_data = {
            "server": {
                "host": "127.0.0.1",
                "port": 9000,
                "cors_origins": ["http://localhost:3000"],
                "debug": True
            },
            "agents": {
                "gmail": {
                    "enabled": True,
                    "timeout_seconds": 60
                }
            }
        }

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            config = APIConfig.from_file(temp_path)

            assert config.server.host == "127.0.0.1"
            assert config.server.port == 9000
            assert config.server.cors_origins == ["http://localhost:3000"]
            assert config.server.debug is True
            assert "gmail" in config.agents
            assert config.agents["gmail"].enabled is True
            assert config.agents["gmail"].timeout_seconds == 60
        finally:
            temp_path.unlink()

    def test_api_config_from_missing_file(self):
        """Test APIConfig returns defaults when file doesn't exist."""
        config = APIConfig.from_file(Path("/nonexistent/config.json"))

        # Should return default config
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8000
        assert config.agents == {}

    def test_api_config_partial_data(self):
        """Test APIConfig handles partial config data."""
        config_data = {
            "server": {
                "port": 5000
            }
        }

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            config = APIConfig.from_file(temp_path)

            # Specified value should be used
            assert config.server.port == 5000
            # Other values should be defaults
            assert config.server.host == "0.0.0.0"
            assert config.server.cors_origins == ["*"]
        finally:
            temp_path.unlink()

    def test_default_config_path(self):
        """Test default config path points to correct location."""
        path = APIConfig.default_config_path()
        assert path.name == "api_config.json"
        assert "configs" in str(path)


class TestAPIServer:
    """Test suite for FastAPI server creation."""

    def test_create_app_returns_fastapi_instance(self):
        """Test create_app returns a FastAPI instance."""
        from fastapi import FastAPI

        test_app = create_app()
        assert isinstance(test_app, FastAPI)

    def test_app_has_correct_title(self):
        """Test app has correct title."""
        test_app = create_app()
        assert test_app.title == "Clarvis API"

    def test_app_has_correct_version(self):
        """Test app has correct version."""
        test_app = create_app()
        assert test_app.version == "1.0.0"

    def test_app_includes_routers(self):
        """Test app includes health and gmail routers."""
        test_app = create_app()

        # Check that routes are registered
        routes = [route.path for route in test_app.routes]
        assert "/health" in routes
        assert "/" in routes
        assert "/api/v1/gmail/query" in routes


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_check_returns_200(self, client):
        """Test health endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_response_structure(self, client):
        """Test health endpoint returns correct structure."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "agents" in data

    def test_health_check_status_healthy(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"

    def test_health_check_version(self, client):
        """Test health endpoint returns correct version."""
        response = client.get("/health")
        data = response.json()

        assert data["version"] == "1.0.0"

    def test_health_check_gmail_agent_available(self, client):
        """Test health endpoint shows gmail agent as available."""
        response = client.get("/health")
        data = response.json()

        assert data["agents"]["gmail"] == "available"

    def test_root_endpoint_returns_200(self, client):
        """Test root endpoint returns 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_endpoint_response_structure(self, client):
        """Test root endpoint returns correct structure."""
        response = client.get("/")
        data = response.json()

        assert data["name"] == "Clarvis API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"

    def test_docs_endpoint_returns_200(self, client):
        """Test docs endpoint is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200


class TestGmailEndpoints:
    """Test suite for Gmail API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_gmail_query_empty_query_returns_400(self, client):
        """Test empty query returns 400 Bad Request."""
        response = client.post(
            "/api/v1/gmail/query",
            json={"query": ""}
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_gmail_query_whitespace_only_returns_400(self, client):
        """Test whitespace-only query returns 400 Bad Request."""
        response = client.post(
            "/api/v1/gmail/query",
            json={"query": "   "}
        )
        assert response.status_code == 400

    def test_gmail_query_missing_query_field_returns_422(self, client):
        """Test missing query field returns 422 Unprocessable Entity."""
        response = client.post(
            "/api/v1/gmail/query",
            json={}
        )
        assert response.status_code == 422

    def test_gmail_query_invalid_json_returns_422(self, client):
        """Test invalid JSON returns 422."""
        response = client.post(
            "/api/v1/gmail/query",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    @patch('clarvis_agents.api.routes.gmail.create_gmail_agent')
    def test_gmail_query_success(self, mock_create_agent, client):
        """Test successful Gmail query."""
        # Mock the agent
        mock_agent = MagicMock()
        mock_agent.check_emails.return_value = "Found 3 unread emails"
        mock_create_agent.return_value = mock_agent

        response = client.post(
            "/api/v1/gmail/query",
            json={"query": "List my unread emails"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["response"] == "Found 3 unread emails"
        assert data["error"] is None

    @patch('clarvis_agents.api.routes.gmail.create_gmail_agent')
    def test_gmail_query_agent_called_with_read_only(self, mock_create_agent, client):
        """Test Gmail agent is created with read_only=True."""
        mock_agent = MagicMock()
        mock_agent.check_emails.return_value = "Response"
        mock_create_agent.return_value = mock_agent

        client.post(
            "/api/v1/gmail/query",
            json={"query": "Test query"}
        )

        mock_create_agent.assert_called_once_with(read_only=True)

    @patch('clarvis_agents.api.routes.gmail.create_gmail_agent')
    def test_gmail_query_passes_query_to_agent(self, mock_create_agent, client):
        """Test query is passed to agent's check_emails method."""
        mock_agent = MagicMock()
        mock_agent.check_emails.return_value = "Response"
        mock_create_agent.return_value = mock_agent

        test_query = "Find emails from john@example.com"
        client.post(
            "/api/v1/gmail/query",
            json={"query": test_query}
        )

        mock_agent.check_emails.assert_called_once_with(test_query)

    @patch('clarvis_agents.api.routes.gmail.create_gmail_agent')
    def test_gmail_query_handles_agent_exception(self, mock_create_agent, client):
        """Test Gmail query handles agent exceptions gracefully."""
        mock_agent = MagicMock()
        mock_agent.check_emails.side_effect = Exception("MCP connection failed")
        mock_create_agent.return_value = mock_agent

        response = client.post(
            "/api/v1/gmail/query",
            json={"query": "Test query"}
        )

        assert response.status_code == 200  # Returns 200 with error in body
        data = response.json()
        assert data["success"] is False
        assert data["response"] == ""
        assert "MCP connection failed" in data["error"]


class TestGmailModels:
    """Test suite for Gmail request/response models."""

    def test_gmail_query_request_valid(self):
        """Test GmailQueryRequest with valid data."""
        request = GmailQueryRequest(query="Test query")
        assert request.query == "Test query"

    def test_gmail_query_response_success(self):
        """Test GmailQueryResponse for success case."""
        response = GmailQueryResponse(
            response="Found emails",
            success=True,
            error=None
        )
        assert response.response == "Found emails"
        assert response.success is True
        assert response.error is None

    def test_gmail_query_response_failure(self):
        """Test GmailQueryResponse for failure case."""
        response = GmailQueryResponse(
            response="",
            success=False,
            error="Connection failed"
        )
        assert response.response == ""
        assert response.success is False
        assert response.error == "Connection failed"


class TestCORSMiddleware:
    """Test suite for CORS configuration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_cors_allows_any_origin_by_default(self, client):
        """Test CORS allows any origin with default config."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        # CORS preflight should succeed
        assert response.status_code == 200

    def test_cors_headers_present(self, client):
        """Test CORS headers are present in response."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # Check for CORS header
        assert "access-control-allow-origin" in response.headers


# Integration tests (require credentials)
class TestGmailIntegration:
    """Integration tests for Gmail endpoint.

    These tests require Gmail credentials to be configured.
    They are skipped if credentials are not available.
    """

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.integration
    @pytest.mark.skipif(
        not Path.home().joinpath(".gmail-mcp/credentials.json").exists(),
        reason="Gmail credentials not configured"
    )
    def test_gmail_query_real_connection(self, client):
        """Test Gmail query with real MCP connection."""
        response = client.post(
            "/api/v1/gmail/query",
            json={"query": "How many unread emails do I have?"}
        )

        assert response.status_code == 200
        data = response.json()
        # Should either succeed or fail gracefully
        assert "success" in data
        assert "response" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
