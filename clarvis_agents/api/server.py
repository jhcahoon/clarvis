"""FastAPI server for Clarvis agents."""

import asyncio
import sys

# Fix Windows asyncio subprocess support - must be set before any async operations
# This is needed because the Claude Agent SDK spawns subprocesses
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import load_config
from .routes import health_router, gmail_router, orchestrator_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info("Clarvis API server starting up...")
    yield
    logger.info("Clarvis API server shutting down...")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    config = load_config()

    app = FastAPI(
        title="Clarvis API",
        description="API server for Clarvis AI agents",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router)
    app.include_router(gmail_router)
    app.include_router(orchestrator_router)

    return app


# Create the default app instance
app = create_app()
