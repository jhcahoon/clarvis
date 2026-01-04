"""Gmail agent endpoints for Clarvis API."""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...gmail_agent import create_gmail_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/gmail", tags=["gmail"])


class GmailQueryRequest(BaseModel):
    """Request model for Gmail queries."""

    query: str


class GmailQueryResponse(BaseModel):
    """Response model for Gmail queries."""

    response: str
    success: bool
    error: Optional[str] = None


@router.post("/query", response_model=GmailQueryResponse)
async def query_gmail(request: GmailQueryRequest) -> GmailQueryResponse:
    """
    Process a natural language query about emails.

    Args:
        request: The query request containing the natural language query

    Returns:
        The agent's response to the query
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    logger.info(f"Received Gmail query: {request.query[:100]}...")

    try:
        # Create the Gmail agent
        agent = create_gmail_agent(read_only=True)

        # Run the query in a thread pool to avoid blocking
        # since check_emails uses asyncio.run internally
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, agent.check_emails, request.query
        )

        logger.info("Gmail query processed successfully")
        return GmailQueryResponse(response=response, success=True)

    except Exception as e:
        logger.error(f"Error processing Gmail query: {e}", exc_info=True)
        return GmailQueryResponse(
            response="",
            success=False,
            error=str(e)
        )
