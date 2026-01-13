"""Orchestrator endpoints for Clarvis API."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core import AgentResponse
from ...orchestrator import OrchestratorAgent, create_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["orchestrator"])

# Global orchestrator instance (lazy initialization for better startup)
_orchestrator: Optional[OrchestratorAgent] = None


def get_orchestrator() -> OrchestratorAgent:
    """Get or create the global orchestrator instance.

    Returns:
        OrchestratorAgent: The singleton orchestrator instance.
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = create_orchestrator()
        logger.info("Orchestrator initialized")
    return _orchestrator


def reset_orchestrator() -> None:
    """Reset the global orchestrator instance (useful for testing)."""
    global _orchestrator
    _orchestrator = None


class OrchestratorQueryRequest(BaseModel):
    """Request model for orchestrator queries."""

    query: str
    session_id: Optional[str] = None


class OrchestratorQueryResponse(BaseModel):
    """Response model for orchestrator queries."""

    response: str
    success: bool
    agent_name: str
    session_id: str
    error: Optional[str] = None
    metadata: Optional[dict] = None


class AgentCapabilityInfo(BaseModel):
    """Information about an agent capability."""

    name: str
    description: str
    keywords: List[str]
    examples: List[str]


class AgentInfo(BaseModel):
    """Information about a registered agent."""

    name: str
    description: str
    capabilities: List[AgentCapabilityInfo]
    healthy: bool


class AgentsListResponse(BaseModel):
    """Response model for listing agents."""

    agents: List[AgentInfo]
    count: int


@router.post("/query", response_model=OrchestratorQueryResponse)
async def query_orchestrator(
    request: OrchestratorQueryRequest,
) -> OrchestratorQueryResponse:
    """
    Process a natural language query through the orchestrator.

    The orchestrator routes the query to the appropriate agent based on
    intent classification. Supports session continuity via session_id.

    Args:
        request: The query request containing the natural language query
                 and optional session_id for conversation continuity.

    Returns:
        The agent's response including which agent handled the query
        and the session_id for follow-up queries.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    logger.info(f"Received orchestrator query: {request.query[:100]}...")
    if request.session_id:
        logger.info(f"Using session: {request.session_id}")

    try:
        orchestrator = get_orchestrator()

        # Get or create session for context continuity
        context = orchestrator.get_or_create_session(request.session_id)

        # Process the query asynchronously
        response: AgentResponse = await orchestrator.process(
            query=request.query,
            context=context,
        )

        logger.info(
            f"Query processed by {response.agent_name}, success={response.success}"
        )

        return OrchestratorQueryResponse(
            response=response.content,
            success=response.success,
            agent_name=response.agent_name,
            session_id=context.session_id,
            error=response.error,
            metadata=response.metadata,
        )

    except Exception as e:
        logger.error(f"Error processing orchestrator query: {e}", exc_info=True)
        return OrchestratorQueryResponse(
            response="",
            success=False,
            agent_name="orchestrator",
            session_id=request.session_id or "",
            error=str(e),
        )


@router.get("/agents", response_model=AgentsListResponse)
async def list_agents() -> AgentsListResponse:
    """
    List all available agents and their capabilities.

    Returns information about each registered agent including:
    - Agent name and description
    - Capabilities with keywords and examples
    - Current health status

    Returns:
        List of all registered agents with their details.
    """
    logger.info("Listing available agents")

    try:
        orchestrator = get_orchestrator()
        registry = orchestrator._registry

        agents_info: List[AgentInfo] = []

        for agent_name in registry.list_agents():
            agent = registry.get(agent_name)
            if agent is None:
                continue

            # Convert capabilities to response model
            capabilities_info = [
                AgentCapabilityInfo(
                    name=cap.name,
                    description=cap.description,
                    keywords=cap.keywords,
                    examples=cap.examples,
                )
                for cap in agent.capabilities
            ]

            agents_info.append(
                AgentInfo(
                    name=agent.name,
                    description=agent.description,
                    capabilities=capabilities_info,
                    healthy=agent.health_check(),
                )
            )

        logger.info(f"Found {len(agents_info)} registered agents")

        return AgentsListResponse(
            agents=agents_info,
            count=len(agents_info),
        )

    except Exception as e:
        logger.error(f"Error listing agents: {e}", exc_info=True)
        return AgentsListResponse(agents=[], count=0)
