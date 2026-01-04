"""API routes package."""

from .health import router as health_router
from .gmail import router as gmail_router

__all__ = ["health_router", "gmail_router"]
