"""Tests for Orchestrator API endpoints (Phase 6)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient

from clarvis_agents.api.server import create_app, app
from clarvis_agents.api.routes.orchestrator import (
    OrchestratorQueryRequest,
    OrchestratorQueryResponse,
    AgentCapabilityInfo,
    AgentInfo,
    AgentsListResponse,
    reset_orchestrator,
)
from clarvis_agents.core import AgentResponse, AgentCapability, ConversationContext


class TestOrchestratorQueryEndpoint:
    """Test suite for POST /api/v1/query endpoint."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset orchestrator singleton before and after each test."""
        reset_orchestrator()
        yield
        reset_orchestrator()

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_empty_query_returns_400(self, client):
        """Test empty query returns 400 Bad Request."""
        response = client.post("/api/v1/query", json={"query": ""})
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_whitespace_only_returns_400(self, client):
        """Test whitespace-only query returns 400 Bad Request."""
        response = client.post("/api/v1/query", json={"query": "   "})
        assert response.status_code == 400

    def test_missing_query_field_returns_422(self, client):
        """Test missing query field returns 422 Unprocessable Entity."""
        response = client.post("/api/v1/query", json={})
        assert response.status_code == 422

    def test_invalid_json_returns_422(self, client):
        """Test invalid JSON returns 422."""
        response = client.post(
            "/api/v1/query",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    @patch("clarvis_agents.api.routes.orchestrator.create_orchestrator")
    def test_query_success(self, mock_create_orchestrator, client):
        """Test successful orchestrator query."""
        # Mock the orchestrator
        mock_orchestrator = MagicMock()
        mock_context = MagicMock()
        mock_context.session_id = "test-session-123"
        mock_orchestrator.get_or_create_session.return_value = mock_context

        mock_response = AgentResponse(
            content="Hello! How can I help you today?",
            success=True,
            agent_name="orchestrator",
            metadata=None,
            error=None,
        )
        mock_orchestrator.process = AsyncMock(return_value=mock_response)
        mock_create_orchestrator.return_value = mock_orchestrator

        response = client.post("/api/v1/query", json={"query": "hello"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["response"] == "Hello! How can I help you today?"
        assert data["agent_name"] == "orchestrator"
        assert data["session_id"] == "test-session-123"
        assert data["error"] is None

    @patch("clarvis_agents.api.routes.orchestrator.create_orchestrator")
    def test_query_with_session_id(self, mock_create_orchestrator, client):
        """Test query with provided session_id."""
        mock_orchestrator = MagicMock()
        mock_context = MagicMock()
        mock_context.session_id = "existing-session-456"
        mock_orchestrator.get_or_create_session.return_value = mock_context

        mock_response = AgentResponse(
            content="Following up on our conversation",
            success=True,
            agent_name="gmail",
            metadata=None,
            error=None,
        )
        mock_orchestrator.process = AsyncMock(return_value=mock_response)
        mock_create_orchestrator.return_value = mock_orchestrator

        response = client.post(
            "/api/v1/query",
            json={"query": "tell me more", "session_id": "existing-session-456"},
        )

        assert response.status_code == 200
        mock_orchestrator.get_or_create_session.assert_called_once_with(
            "existing-session-456"
        )
        data = response.json()
        assert data["session_id"] == "existing-session-456"

    @patch("clarvis_agents.api.routes.orchestrator.create_orchestrator")
    def test_query_returns_session_id(self, mock_create_orchestrator, client):
        """Test response includes session_id for follow-up queries."""
        mock_orchestrator = MagicMock()
        mock_context = MagicMock()
        mock_context.session_id = "new-session-789"
        mock_orchestrator.get_or_create_session.return_value = mock_context

        mock_response = AgentResponse(
            content="Test response",
            success=True,
            agent_name="orchestrator",
        )
        mock_orchestrator.process = AsyncMock(return_value=mock_response)
        mock_create_orchestrator.return_value = mock_orchestrator

        response = client.post("/api/v1/query", json={"query": "test"})

        data = response.json()
        assert "session_id" in data
        assert data["session_id"] == "new-session-789"

    @patch("clarvis_agents.api.routes.orchestrator.create_orchestrator")
    def test_query_handles_exception(self, mock_create_orchestrator, client):
        """Test query handles orchestrator exceptions gracefully."""
        mock_orchestrator = MagicMock()
        mock_context = MagicMock()
        mock_context.session_id = "test-session"
        mock_orchestrator.get_or_create_session.return_value = mock_context
        mock_orchestrator.process = AsyncMock(
            side_effect=Exception("Connection failed")
        )
        mock_create_orchestrator.return_value = mock_orchestrator

        response = client.post("/api/v1/query", json={"query": "test"})

        assert response.status_code == 200  # Returns 200 with error in body
        data = response.json()
        assert data["success"] is False
        assert data["response"] == ""
        assert "Connection failed" in data["error"]

    @patch("clarvis_agents.api.routes.orchestrator.create_orchestrator")
    def test_query_returns_agent_name(self, mock_create_orchestrator, client):
        """Test response includes which agent handled the query."""
        mock_orchestrator = MagicMock()
        mock_context = MagicMock()
        mock_context.session_id = "test-session"
        mock_orchestrator.get_or_create_session.return_value = mock_context

        mock_response = AgentResponse(
            content="You have 3 unread emails",
            success=True,
            agent_name="gmail",  # Gmail handled this query
        )
        mock_orchestrator.process = AsyncMock(return_value=mock_response)
        mock_create_orchestrator.return_value = mock_orchestrator

        response = client.post(
            "/api/v1/query", json={"query": "check my emails"}
        )

        data = response.json()
        assert data["agent_name"] == "gmail"

    @patch("clarvis_agents.api.routes.orchestrator.create_orchestrator")
    def test_query_returns_metadata(self, mock_create_orchestrator, client):
        """Test response includes metadata when present."""
        mock_orchestrator = MagicMock()
        mock_context = MagicMock()
        mock_context.session_id = "test-session"
        mock_orchestrator.get_or_create_session.return_value = mock_context

        mock_response = AgentResponse(
            content="Response with metadata",
            success=True,
            agent_name="orchestrator",
            metadata={"routing_confidence": 0.95},
        )
        mock_orchestrator.process = AsyncMock(return_value=mock_response)
        mock_create_orchestrator.return_value = mock_orchestrator

        response = client.post("/api/v1/query", json={"query": "test"})

        data = response.json()
        assert data["metadata"] == {"routing_confidence": 0.95}


class TestAgentsEndpoint:
    """Test suite for GET /api/v1/agents endpoint."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset orchestrator singleton before and after each test."""
        reset_orchestrator()
        yield
        reset_orchestrator()

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @patch("clarvis_agents.api.routes.orchestrator.create_orchestrator")
    def test_agents_endpoint_returns_200(self, mock_create_orchestrator, client):
        """Test agents endpoint returns 200 OK."""
        mock_orchestrator = MagicMock()
        mock_registry = MagicMock()
        mock_registry.list_agents.return_value = []
        mock_orchestrator._registry = mock_registry
        mock_create_orchestrator.return_value = mock_orchestrator

        response = client.get("/api/v1/agents")
        assert response.status_code == 200

    @patch("clarvis_agents.api.routes.orchestrator.create_orchestrator")
    def test_agents_endpoint_returns_list_structure(
        self, mock_create_orchestrator, client
    ):
        """Test agents endpoint returns correct structure."""
        mock_orchestrator = MagicMock()
        mock_registry = MagicMock()
        mock_registry.list_agents.return_value = []
        mock_orchestrator._registry = mock_registry
        mock_create_orchestrator.return_value = mock_orchestrator

        response = client.get("/api/v1/agents")
        data = response.json()

        assert "agents" in data
        assert "count" in data
        assert isinstance(data["agents"], list)
        assert isinstance(data["count"], int)

    @patch("clarvis_agents.api.routes.orchestrator.create_orchestrator")
    def test_agents_endpoint_includes_capabilities(
        self, mock_create_orchestrator, client
    ):
        """Test agents endpoint includes agent capabilities."""
        # Create a mock agent with capabilities
        mock_agent = MagicMock()
        mock_agent.name = "gmail"
        mock_agent.description = "Gmail email agent"
        mock_agent.capabilities = [
            AgentCapability(
                name="check_inbox",
                description="Check inbox for emails",
                keywords=["email", "inbox", "unread"],
                examples=["check my emails", "how many unread emails"],
            )
        ]
        mock_agent.health_check.return_value = True

        mock_orchestrator = MagicMock()
        mock_registry = MagicMock()
        mock_registry.list_agents.return_value = ["gmail"]
        mock_registry.get.return_value = mock_agent
        mock_orchestrator._registry = mock_registry
        mock_create_orchestrator.return_value = mock_orchestrator

        response = client.get("/api/v1/agents")
        data = response.json()

        assert data["count"] == 1
        assert len(data["agents"]) == 1

        agent = data["agents"][0]
        assert agent["name"] == "gmail"
        assert agent["description"] == "Gmail email agent"
        assert agent["healthy"] is True
        assert len(agent["capabilities"]) == 1

        cap = agent["capabilities"][0]
        assert cap["name"] == "check_inbox"
        assert "email" in cap["keywords"]

    @patch("clarvis_agents.api.routes.orchestrator.create_orchestrator")
    def test_agents_endpoint_includes_health(
        self, mock_create_orchestrator, client
    ):
        """Test agents endpoint includes health status for each agent."""
        mock_agent = MagicMock()
        mock_agent.name = "gmail"
        mock_agent.description = "Gmail agent"
        mock_agent.capabilities = []
        mock_agent.health_check.return_value = False  # Unhealthy agent

        mock_orchestrator = MagicMock()
        mock_registry = MagicMock()
        mock_registry.list_agents.return_value = ["gmail"]
        mock_registry.get.return_value = mock_agent
        mock_orchestrator._registry = mock_registry
        mock_create_orchestrator.return_value = mock_orchestrator

        response = client.get("/api/v1/agents")
        data = response.json()

        assert data["agents"][0]["healthy"] is False

    @patch("clarvis_agents.api.routes.orchestrator.create_orchestrator")
    def test_agents_endpoint_handles_exception(
        self, mock_create_orchestrator, client
    ):
        """Test agents endpoint handles exceptions gracefully."""
        mock_create_orchestrator.side_effect = Exception("Initialization failed")

        response = client.get("/api/v1/agents")

        assert response.status_code == 200
        data = response.json()
        assert data["agents"] == []
        assert data["count"] == 0


class TestOrchestratorModels:
    """Test suite for orchestrator request/response models."""

    def test_query_request_valid(self):
        """Test OrchestratorQueryRequest with valid data."""
        request = OrchestratorQueryRequest(query="Test query")
        assert request.query == "Test query"
        assert request.session_id is None

    def test_query_request_with_session_id(self):
        """Test OrchestratorQueryRequest with session_id."""
        request = OrchestratorQueryRequest(
            query="Test query", session_id="abc-123"
        )
        assert request.query == "Test query"
        assert request.session_id == "abc-123"

    def test_query_response_success(self):
        """Test OrchestratorQueryResponse for success case."""
        response = OrchestratorQueryResponse(
            response="Hello!",
            success=True,
            agent_name="orchestrator",
            session_id="session-123",
            error=None,
            metadata=None,
        )
        assert response.response == "Hello!"
        assert response.success is True
        assert response.agent_name == "orchestrator"
        assert response.session_id == "session-123"
        assert response.error is None

    def test_query_response_failure(self):
        """Test OrchestratorQueryResponse for failure case."""
        response = OrchestratorQueryResponse(
            response="",
            success=False,
            agent_name="orchestrator",
            session_id="session-123",
            error="Connection failed",
        )
        assert response.response == ""
        assert response.success is False
        assert response.error == "Connection failed"

    def test_agent_capability_info(self):
        """Test AgentCapabilityInfo model."""
        cap = AgentCapabilityInfo(
            name="check_inbox",
            description="Check inbox",
            keywords=["email", "inbox"],
            examples=["check my emails"],
        )
        assert cap.name == "check_inbox"
        assert cap.keywords == ["email", "inbox"]

    def test_agent_info(self):
        """Test AgentInfo model."""
        cap = AgentCapabilityInfo(
            name="capability",
            description="A capability",
            keywords=[],
            examples=[],
        )
        agent = AgentInfo(
            name="gmail",
            description="Gmail agent",
            capabilities=[cap],
            healthy=True,
        )
        assert agent.name == "gmail"
        assert agent.healthy is True
        assert len(agent.capabilities) == 1

    def test_agents_list_response(self):
        """Test AgentsListResponse model."""
        response = AgentsListResponse(agents=[], count=0)
        assert response.agents == []
        assert response.count == 0


class TestOrchestratorRouteRegistration:
    """Test suite for route registration in FastAPI app."""

    def test_routes_registered_in_app(self):
        """Test orchestrator routes are registered in the app."""
        test_app = create_app()
        routes = [route.path for route in test_app.routes]

        assert "/api/v1/query" in routes
        assert "/api/v1/agents" in routes

    def test_existing_routes_preserved(self):
        """Test existing gmail routes are still present."""
        test_app = create_app()
        routes = [route.path for route in test_app.routes]

        # Gmail endpoint should still exist
        assert "/api/v1/gmail/query" in routes
        # Health endpoints should still exist
        assert "/health" in routes
        assert "/" in routes

    def test_docs_include_orchestrator_endpoints(self):
        """Test OpenAPI docs include orchestrator endpoints."""
        client = TestClient(app)
        response = client.get("/openapi.json")

        assert response.status_code == 200
        openapi = response.json()

        # Check paths include orchestrator endpoints
        assert "/api/v1/query" in openapi["paths"]
        assert "/api/v1/agents" in openapi["paths"]


class TestHealthEndpointUpdates:
    """Test suite for health endpoint updates."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_includes_orchestrator(self, client):
        """Test health endpoint shows orchestrator in agents list."""
        response = client.get("/health")
        data = response.json()

        assert "orchestrator" in data["agents"]
        assert data["agents"]["orchestrator"] == "available"

    def test_health_preserves_gmail(self, client):
        """Test health endpoint still shows gmail agent."""
        response = client.get("/health")
        data = response.json()

        assert "gmail" in data["agents"]
        assert data["agents"]["gmail"] == "available"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
