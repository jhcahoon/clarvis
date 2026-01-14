"""Orchestrator agent for coordinating multi-agent responses."""

import logging
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from anthropic import Anthropic

from ..core import (
    AgentCapability,
    AgentRegistry,
    AgentResponse,
    BaseAgent,
    ConversationContext,
)
from .config import OrchestratorConfig, load_config
from .router import IntentRouter, RoutingDecision

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Central orchestrator that routes queries to appropriate agents.

    The orchestrator:
    1. Manages conversation sessions
    2. Routes queries using IntentRouter
    3. Delegates to specialized agents or handles directly
    4. Maintains conversation context across turns
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        registry: AgentRegistry,
        router: Optional[IntentRouter] = None,
        anthropic_client: Optional[Anthropic] = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            config: Orchestrator configuration.
            registry: Agent registry with available agents.
            router: Optional custom router. Defaults to IntentRouter.
            anthropic_client: Optional Anthropic client for direct handling.
        """
        self._config = config
        self._registry = registry
        self._router = router or IntentRouter(registry, config)
        self._client = anthropic_client
        self._sessions: dict[str, ConversationContext] = {}
        self._session_timestamps: dict[str, datetime] = {}

    @property
    def name(self) -> str:
        """Unique identifier for this agent."""
        return "orchestrator"

    @property
    def description(self) -> str:
        """Human-readable description of what this agent does."""
        return "Central coordinator that routes queries to appropriate specialist agents"

    @property
    def capabilities(self) -> list[AgentCapability]:
        """List of capabilities this agent provides."""
        return [
            AgentCapability(
                name="query_routing",
                description="Routes queries to appropriate specialist agents",
                keywords=["help", "assist", "question"],
                examples=["check my emails", "what's the weather", "hello"],
            ),
            AgentCapability(
                name="conversation_management",
                description="Manages multi-turn conversations with context",
                keywords=["follow-up", "more", "continue"],
                examples=["tell me more", "what about the first one"],
            ),
        ]

    def health_check(self) -> bool:
        """Check if orchestrator and all registered agents are healthy.

        Returns:
            True if the orchestrator is operational.
        """
        try:
            # Check registry is accessible
            agent_health = self._registry.health_check_all()
            # Orchestrator is healthy if at least one agent is healthy
            # or if no agents are registered yet
            return any(agent_health.values()) if agent_health else True
        except Exception:
            return False

    def get_or_create_session(
        self, session_id: Optional[str] = None
    ) -> ConversationContext:
        """Get an existing session or create a new one.

        Args:
            session_id: Optional session ID. If None, creates new session.

        Returns:
            ConversationContext for the session.
        """
        # Clean up expired sessions first
        self._cleanup_expired_sessions()

        if session_id and session_id in self._sessions:
            # Update timestamp
            self._session_timestamps[session_id] = datetime.now()
            return self._sessions[session_id]

        # Create new session
        if session_id:
            context = ConversationContext(session_id=session_id)
        else:
            context = ConversationContext()

        self._sessions[context.session_id] = context
        self._session_timestamps[context.session_id] = datetime.now()
        return context

    def _cleanup_expired_sessions(self) -> None:
        """Remove sessions that have exceeded the timeout."""
        timeout = timedelta(minutes=self._config.session_timeout_minutes)
        now = datetime.now()

        expired = [
            sid
            for sid, timestamp in self._session_timestamps.items()
            if now - timestamp > timeout
        ]

        for sid in expired:
            del self._sessions[sid]
            del self._session_timestamps[sid]
            logger.debug(f"Cleaned up expired session: {sid}")

    def _get_client(self) -> Anthropic:
        """Get or create Anthropic client.

        Returns:
            Anthropic client instance.

        Raises:
            ValueError: If ANTHROPIC_API_KEY is not set.
        """
        if self._client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            self._client = Anthropic(api_key=api_key)
        return self._client

    async def _handle_direct(
        self,
        query: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """Handle queries directly without delegating to agents.

        Used for greetings, thanks, and general questions.

        Args:
            query: The user's query.
            context: Conversation context.

        Returns:
            AgentResponse with direct response.
        """
        try:
            client = self._get_client()

            # Build system prompt
            system_prompt = """You are Clarvis, a helpful AI home assistant.
You can help with email, calendar, weather, and other tasks through specialized agents.
For greetings, thanks, and general questions, respond naturally and helpfully.
Keep responses concise and friendly."""

            # Include recent context
            messages = []
            if context.turns:
                recent = context.get_recent_context(n=2)
                messages.append(
                    {
                        "role": "user",
                        "content": f"Recent conversation:\n{recent}\n\nNew query: {query}",
                    }
                )
            else:
                messages.append({"role": "user", "content": query})

            response = client.messages.create(
                model=self._config.model,
                max_tokens=500,
                system=system_prompt,
                messages=messages,
            )

            content = (
                response.content[0].text
                if response.content
                else "Hello! How can I help you?"
            )

            return AgentResponse(
                content=content,
                success=True,
                agent_name=self.name,
                metadata={"handled_directly": True},
            )

        except Exception as e:
            logger.error(f"Error in direct handling: {e}")
            # Fallback to simple response
            return AgentResponse(
                content="Hello! I'm Clarvis, your AI assistant. How can I help you today?",
                success=True,
                agent_name=self.name,
                metadata={"handled_directly": True, "fallback": True},
            )

    async def _handle_single_agent(
        self,
        query: str,
        decision: RoutingDecision,
        context: ConversationContext,
    ) -> AgentResponse:
        """Delegate query to a single agent.

        Args:
            query: The user's query.
            decision: Routing decision with agent name.
            context: Conversation context.

        Returns:
            AgentResponse from the delegated agent.
        """
        agent_name = decision.agent_name
        agent = self._registry.get(agent_name)

        if agent is None:
            logger.warning(f"Agent '{agent_name}' not found in registry")
            return await self._handle_fallback(query, context)

        logger.info(f"Delegating to agent: {agent_name}")

        try:
            response = await agent.process(query, context)
            return response
        except Exception as e:
            logger.error(f"Error from agent {agent_name}: {e}", exc_info=True)
            return AgentResponse(
                content="I tried to help with your request, but encountered an issue. Please try again.",
                success=False,
                agent_name=agent_name,
                error=str(e),
            )

    async def _handle_fallback(
        self,
        query: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """Handle queries that couldn't be routed to any agent.

        Args:
            query: The user's query.
            context: Conversation context.

        Returns:
            AgentResponse with fallback message.
        """
        logger.info("Using fallback handling for unmatched query")

        # List available agents for user guidance
        available_agents = self._registry.list_agents()

        if available_agents:
            agent_list = ", ".join(available_agents)
            content = (
                f"I'm not sure how to help with that specific request. "
                f"I can assist with: {agent_list}. "
                f"Could you rephrase your question or ask about one of these topics?"
            )
        else:
            content = (
                "I'm not sure how to help with that request. "
                "Could you try rephrasing your question?"
            )

        return AgentResponse(
            content=content,
            success=True,
            agent_name=self.name,
            metadata={"fallback": True},
        )

    async def process(
        self,
        query: str,
        context: Optional[ConversationContext] = None,
        session_id: Optional[str] = None,
    ) -> AgentResponse:
        """Process a query by routing to appropriate handler.

        Args:
            query: The user's query.
            context: Optional existing context. If provided, session_id is ignored.
            session_id: Optional session ID for session management.

        Returns:
            AgentResponse from the handling agent or direct response.
        """
        # Get or create context
        if context is None:
            context = self.get_or_create_session(session_id)

        logger.info(f"Processing query: {query[:50]}... (session: {context.session_id})")

        try:
            # Route the query
            decision = await self._router.route(query, context)
            logger.debug(f"Routing decision: {decision}")

            # Handle based on decision
            if decision.handle_directly:
                response = await self._handle_direct(query, context)
            elif decision.agent_name:
                response = await self._handle_single_agent(query, decision, context)
            else:
                response = await self._handle_fallback(query, context)

            # Update context with this turn
            context.add_turn(query, response.content, response.agent_name)

            return response

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return AgentResponse(
                content="I'm sorry, I encountered an error processing your request. Please try again.",
                success=False,
                agent_name=self.name,
                error=str(e),
            )

    async def stream(
        self,
        query: str,
        context: Optional[ConversationContext] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks by routing to appropriate handler.

        Args:
            query: The user's query.
            context: Optional existing context. If provided, session_id is ignored.
            session_id: Optional session ID for session management.

        Yields:
            String chunks of the response as they become available.
        """
        # Get or create context
        if context is None:
            context = self.get_or_create_session(session_id)

        logger.info(
            f"Streaming query: {query[:50]}... (session: {context.session_id})"
        )

        collected_response = ""

        try:
            # Route the query
            decision = await self._router.route(query, context)
            logger.debug(f"Routing decision: {decision}")

            # Stream based on decision
            if decision.handle_directly:
                async for chunk in self._stream_direct(query, context):
                    collected_response += chunk
                    yield chunk
            elif decision.agent_name:
                async for chunk in self._stream_single_agent(
                    query, decision, context
                ):
                    collected_response += chunk
                    yield chunk
            else:
                async for chunk in self._stream_fallback(query, context):
                    collected_response += chunk
                    yield chunk

            # Update context with the complete response
            context.add_turn(query, collected_response, decision.agent_name or self.name)

        except Exception as e:
            logger.error(f"Error streaming query: {e}", exc_info=True)
            error_msg = "I'm sorry, I encountered an error processing your request."
            yield error_msg

    async def _stream_direct(
        self,
        query: str,
        context: ConversationContext,
    ) -> AsyncGenerator[str, None]:
        """Stream direct response without delegating to agents.

        Used for greetings, thanks, and general questions.

        Args:
            query: The user's query.
            context: Conversation context.

        Yields:
            String chunks of the response.
        """
        try:
            client = self._get_client()

            system_prompt = """You are Clarvis, a helpful AI home assistant.
You can help with email, calendar, weather, and other tasks through specialized agents.
For greetings, thanks, and general questions, respond naturally and helpfully.
Keep responses concise and friendly."""

            messages = []
            if context.turns:
                recent = context.get_recent_context(n=2)
                messages.append(
                    {
                        "role": "user",
                        "content": f"Recent conversation:\n{recent}\n\nNew query: {query}",
                    }
                )
            else:
                messages.append({"role": "user", "content": query})

            # Use streaming API
            with client.messages.stream(
                model=self._config.model,
                max_tokens=500,
                system=system_prompt,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Error in direct streaming: {e}")
            yield "Hello! I'm Clarvis, your AI assistant. How can I help you today?"

    async def _stream_single_agent(
        self,
        query: str,
        decision: RoutingDecision,
        context: ConversationContext,
    ) -> AsyncGenerator[str, None]:
        """Stream response from a single delegated agent.

        Args:
            query: The user's query.
            decision: Routing decision with agent name.
            context: Conversation context.

        Yields:
            String chunks from the delegated agent.
        """
        agent_name = decision.agent_name
        agent = self._registry.get(agent_name)

        if agent is None:
            logger.warning(f"Agent '{agent_name}' not found in registry")
            async for chunk in self._stream_fallback(query, context):
                yield chunk
            return

        logger.info(f"Streaming from agent: {agent_name}")

        try:
            async for chunk in agent.stream(query, context):
                yield chunk
        except Exception as e:
            logger.error(f"Error streaming from agent {agent_name}: {e}", exc_info=True)
            yield "I tried to help with your request, but encountered an issue. Please try again."

    async def _stream_fallback(
        self,
        query: str,
        context: ConversationContext,
    ) -> AsyncGenerator[str, None]:
        """Stream fallback response for unmatched queries.

        Args:
            query: The user's query.
            context: Conversation context.

        Yields:
            String chunks of the fallback message.
        """
        logger.info("Using fallback streaming for unmatched query")

        available_agents = self._registry.list_agents()

        if available_agents:
            agent_list = ", ".join(available_agents)
            content = (
                f"I'm not sure how to help with that specific request. "
                f"I can assist with: {agent_list}. "
                f"Could you rephrase your question or ask about one of these topics?"
            )
        else:
            content = (
                "I'm not sure how to help with that request. "
                "Could you try rephrasing your question?"
            )

        yield content


def create_orchestrator(
    config: Optional[OrchestratorConfig] = None,
) -> OrchestratorAgent:
    """Factory function to create and configure an orchestrator.

    Args:
        config: Optional config. Uses default if not provided.

    Returns:
        Configured OrchestratorAgent instance.
    """
    config = config or load_config()
    registry = AgentRegistry()

    # Future: Register agents that implement BaseAgent
    # Gmail agent will be registered here once Issue #15 is complete
    # and GmailAgent implements BaseAgent
    try:
        from ..gmail_agent import GmailAgent

        # Check if GmailAgent implements BaseAgent
        if issubclass(GmailAgent, BaseAgent):
            from ..gmail_agent import create_gmail_agent

            gmail_agent = create_gmail_agent(read_only=True)
            registry.register(gmail_agent)
            logger.info("Registered Gmail agent with orchestrator")
    except (ImportError, TypeError):
        # GmailAgent not available or doesn't implement BaseAgent yet
        logger.debug("Gmail agent not registered (doesn't implement BaseAgent)")

    return OrchestratorAgent(config=config, registry=registry)
