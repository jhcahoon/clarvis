"""Health check endpoints for Clarvis API."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        Health status of the API and available agents
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "agents": {
            "gmail": "available"
        }
    }


@router.get("/")
async def root() -> dict:
    """
    Root endpoint.

    Returns:
        Basic API information
    """
    return {
        "name": "Clarvis API",
        "version": "1.0.0",
        "docs": "/docs"
    }
