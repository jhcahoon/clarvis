# Agent Architecture

This document describes the multi-agent orchestration pattern in Clarvis, including the core abstractions, routing logic, and how specialist agents interact with the orchestrator.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Clarvis Multi-Agent System                         │
│                                                                              │
│  ┌────────────────┐                                                          │
│  │   User Query   │                                                          │
│  │   (Voice/API)  │                                                          │
│  └───────┬────────┘                                                          │
│          │                                                                   │
│          ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        OrchestratorAgent                                │ │
│  │  ┌──────────────────┐    ┌─────────────────┐    ┌──────────────────┐   │ │
│  │  │  IntentRouter    │    │  AgentRegistry  │    │ ConversationCtx  │   │ │
│  │  │  ┌────────────┐  │    │   (Singleton)   │    │  (Session State) │   │ │
│  │  │  │ Classifier │  │    │                 │    │                  │   │ │
│  │  │  └────────────┘  │    │  gmail ────────►├────│  session_id      │   │ │
│  │  │        │         │    │  ski ──────────►│    │  turns[]         │   │ │
│  │  │  [Code Routing]  │    │  notes ────────►│    │  last_agent      │   │ │
│  │  │        │         │    │                 │    │                  │   │ │
│  │  │  [LLM Routing]   │    │                 │    │                  │   │ │
│  │  └──────────────────┘    └─────────────────┘    └──────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│          │                                                                   │
│          ▼                                                                   │
│  ┌───────────────────┬────────────────────┬────────────────────┐            │
│  │    GmailAgent     │     SkiAgent       │    NotesAgent      │            │
│  │  (External MCP)   │  (Native Tools)    │  (Native Tools)    │            │
│  │                   │                    │                    │            │
│  │ ┌───────────────┐ │ ┌────────────────┐ │ ┌────────────────┐ │            │
│  │ │ Gmail MCP     │ │ │ httpx fetch    │ │ │ Local JSON     │ │            │
│  │ │ Server (npx)  │ │ │ tools          │ │ │ storage tools  │ │            │
│  │ └───────────────┘ │ └────────────────┘ │ └────────────────┘ │            │
│  └───────────────────┴────────────────────┴────────────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Abstractions

The multi-agent system is built on three core abstractions in `clarvis_agents/core/`:

### BaseAgent (`base_agent.py`)

Abstract base class that all agents must implement:

```python
class BaseAgent(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this agent does."""

    @property
    @abstractmethod
    def capabilities(self) -> list[AgentCapability]:
        """List of capabilities this agent provides."""

    @abstractmethod
    async def process(self, query: str, context: Optional[ConversationContext]) -> AgentResponse:
        """Process a query and return a response."""

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the agent is operational."""

    async def stream(self, query: str, context: Optional[ConversationContext]) -> AsyncGenerator[str, None]:
        """Stream response chunks (optional, defaults to process() fallback)."""
```

**Supporting dataclasses:**

- `AgentResponse`: Standardized response with `content`, `success`, `agent_name`, `metadata`, `error`
- `AgentCapability`: Describes what an agent can do with `name`, `description`, `keywords`, `examples`

### AgentRegistry (`agent_registry.py`)

Singleton registry for managing agent registration and discovery:

```
┌─────────────────────────────────────┐
│         AgentRegistry               │
│         (Singleton)                 │
├─────────────────────────────────────┤
│  _agents: dict[str, BaseAgent]      │
├─────────────────────────────────────┤
│  register(agent)                    │
│  unregister(name)                   │
│  get(name) -> BaseAgent | None      │
│  list_agents() -> list[str]         │
│  get_all_capabilities()             │
│  health_check_all()                 │
│  clear()                            │
└─────────────────────────────────────┘
```

Key behaviors:
- **Singleton pattern**: Only one instance exists across the application
- **Register by name**: Agents are keyed by their `name` property
- **Capability aggregation**: `get_all_capabilities()` collects capabilities from all agents for routing

### ConversationContext (`context.py`)

Tracks conversation state across multiple turns:

```
┌─────────────────────────────────────┐
│       ConversationContext           │
├─────────────────────────────────────┤
│  session_id: str (UUID)             │
│  turns: list[ConversationTurn]      │
│  last_agent: str | None             │
├─────────────────────────────────────┤
│  add_turn(query, response, agent)   │
│  get_recent_context(n=3) -> str     │
│  should_continue_with_agent(query)  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│        ConversationTurn             │
├─────────────────────────────────────┤
│  query: str                         │
│  response: str                      │
│  agent_used: str                    │
│  timestamp: datetime                │
└─────────────────────────────────────┘
```

**Follow-up detection**: `should_continue_with_agent()` detects follow-up queries using:
- Follow-up phrases: "what about", "tell me more", "also", etc.
- Pronoun detection in short queries: "it", "they", "that", etc.

## Orchestrator Routing

The orchestrator uses a hybrid routing system combining fast code-based classification with LLM fallback.

### Routing Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IntentRouter.route()                               │
│                                                                              │
│   Query ─────────┬──────────────────────────────────────────────────────────►│
│                  │                                                           │
│                  ▼                                                           │
│   ┌──────────────────────────┐                                              │
│   │ 1. Check Follow-up       │  context.should_continue_with_agent()        │
│   │    (Last agent match?)   │───► YES ───► Return: Route to last_agent     │
│   └────────────┬─────────────┘                                              │
│                │ NO                                                          │
│                ▼                                                             │
│   ┌──────────────────────────┐                                              │
│   │ 2. Check Direct Handling │  Greetings: "hello", "hi", "hey"             │
│   │    (Greeting/thanks?)    │  Thanks: "thank you", "thanks", "great"      │
│   │                          │───► YES ───► Return: handle_directly=True    │
│   └────────────┬─────────────┘                                              │
│                │ NO                                                          │
│                ▼                                                             │
│   ┌──────────────────────────┐                                              │
│   │ 3. Code-Based Classify   │  IntentClassifier.classify()                 │
│   │    (Keyword + Pattern)   │  Keyword: +0.2/match (cap 0.6)               │
│   │                          │  Pattern: +0.3/match (cap 0.6)               │
│   └────────────┬─────────────┘                                              │
│                │                                                             │
│                ▼                                                             │
│   ┌──────────────────────────┐                                              │
│   │ confidence >= 0.7?       │───► YES ───► Return: Route to agent          │
│   │ (threshold)              │                                              │
│   └────────────┬─────────────┘                                              │
│                │ NO                                                          │
│                ▼                                                             │
│   ┌──────────────────────────┐                                              │
│   │ 4. LLM Routing           │  Claude 3.5 Haiku (router_model)             │
│   │    (Ambiguous queries)   │  Parses: AGENT, CONFIDENCE, REASONING        │
│   └──────────────────────────┘───► Return: RoutingDecision                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### IntentClassifier

Fast code-based classification using keywords and regex patterns:

**Scoring algorithm:**
- Keyword match: +0.2 per keyword (capped at 0.6)
- Pattern match: +0.3 per pattern (capped at 0.6)
- Total score: capped at 1.0
- Ambiguity: If second-best agent is within 0.1 of best, needs LLM

**Agent patterns (from `classifier.py`):**

| Agent | Keywords | Example Patterns |
|-------|----------|------------------|
| gmail | email, inbox, unread, mail, messages | `\b(check\|read).*\b(email\|inbox)\b` |
| ski | ski, snow, meadows, hood, powder, lifts | `\b(ski\|snow).*\b(conditions\|meadows)\b` |
| notes | note, list, reminder, grocery, shopping | `\b(add\|put).*\b(to\|on).*\b(list)\b` |

### RoutingDecision

Result of the routing process:

```python
@dataclass
class RoutingDecision:
    agent_name: Optional[str]      # Target agent or None
    confidence: float              # 0.0 to 1.0
    reasoning: str                 # Why this decision was made
    handle_directly: bool = False  # Orchestrator handles directly
```

## Request Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     OrchestratorAgent.process()                              │
│                                                                              │
│  1. Get/Create Session                                                       │
│     ┌──────────────────────────────────────────┐                            │
│     │ session_id provided?                      │                            │
│     │  YES → get_or_create_session(session_id) │                            │
│     │  NO  → create new ConversationContext    │                            │
│     └──────────────────────────────────────────┘                            │
│                         │                                                    │
│  2. Route Query         ▼                                                    │
│     ┌──────────────────────────────────────────┐                            │
│     │ decision = router.route(query, context)  │                            │
│     └──────────────────────────────────────────┘                            │
│                         │                                                    │
│  3. Handle Based        ▼                                                    │
│     on Decision   ┌─────────────────────────────────────┐                   │
│                   │                                     │                   │
│     ┌─────────────┴──────────┬──────────────────────────┴─────────────┐     │
│     │                        │                                        │     │
│     ▼                        ▼                                        ▼     │
│ ┌────────────┐        ┌─────────────┐                          ┌──────────┐ │
│ │ Direct     │        │ Single      │                          │ Fallback │ │
│ │ Handling   │        │ Agent       │                          │          │ │
│ │            │        │ Delegation  │                          │          │ │
│ │ Claude API │        │             │                          │ "I can   │ │
│ │ for simple │        │ agent.      │                          │ help     │ │
│ │ responses  │        │   process() │                          │ with..." │ │
│ └────────────┘        └─────────────┘                          └──────────┘ │
│                                                                              │
│  4. Update Context                                                           │
│     ┌──────────────────────────────────────────┐                            │
│     │ context.add_turn(query, response, agent) │                            │
│     └──────────────────────────────────────────┘                            │
│                                                                              │
│  5. Return AgentResponse                                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Streaming Architecture

For real-time voice responses, the orchestrator supports streaming:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     OrchestratorAgent.stream()                               │
│                                                                              │
│   ┌────────────────────┐                                                    │
│   │ Route Decision     │                                                    │
│   └─────────┬──────────┘                                                    │
│             │                                                                │
│   ┌─────────┴──────────┬───────────────────┬────────────────────┐           │
│   │                    │                   │                    │           │
│   ▼                    ▼                   ▼                    ▼           │
│ ┌────────────┐   ┌─────────────┐    ┌─────────────┐     ┌──────────┐        │
│ │ _stream_   │   │ _stream_    │    │ agent.      │     │ _stream_ │        │
│ │ direct()   │   │ single_     │    │ stream()    │     │ fallback │        │
│ │            │   │ agent()     │    │             │     │ ()       │        │
│ │ Claude API │   │             │    │             │     │          │        │
│ │ streaming  │   │ ┌─────────┐ │    │ Yields      │     │ Single   │        │
│ │            │   │ │Announce │ │    │ chunks      │     │ chunk    │        │
│ │ Yields     │   │ │"Check-  │ │    │             │     │          │        │
│ │ chunks     │   │ │ing..."  │ │    │             │     │          │        │
│ │            │   │ └─────────┘ │    │             │     │          │        │
│ └────────────┘   └─────────────┘    └─────────────┘     └──────────┘        │
│                                                                              │
│   Routing Announcements (for voice feedback):                               │
│   ┌──────────────────────────────────────────┐                              │
│   │ gmail  → "Checking your email. "         │                              │
│   │ ski    → "Checking ski conditions. "     │                              │
│   │ notes  → "Checking your notes. "         │                              │
│   └──────────────────────────────────────────┘                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Specialist Agent Patterns

### Pattern 1: External MCP Server (GmailAgent)

Uses an external MCP server spawned via `npx`:

```
┌───────────────────────────────────────────────────────────────┐
│                      GmailAgent                               │
│                                                               │
│  ┌────────────────┐                                           │
│  │ ClaudeSDKClient│                                           │
│  │                │                                           │
│  │  mcp_servers:  │                                           │
│  │    gmail:      │───────────┐                               │
│  │      type:     │           │                               │
│  │        stdio   │           ▼                               │
│  │      command:  │  ┌─────────────────────────────────────┐  │
│  │        npx     │  │ @gongrzhe/server-gmail-autoauth-mcp │  │
│  │      args:     │  │                                     │  │
│  │        ["-y",  │  │  OAuth via ~/.gmail-mcp/            │  │
│  │        ...]    │  │  Tools: search, read, send, etc.    │  │
│  └────────────────┘  └─────────────────────────────────────┘  │
│                                                               │
│  Config: read_only=True (blocks send/delete/modify)           │
│  Rate Limiting: sliding window algorithm                      │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Pattern 2: Native SDK Tools (SkiAgent, NotesAgent)

Uses native Python tools registered with the SDK:

```
┌───────────────────────────────────────────────────────────────┐
│                   SkiAgent / NotesAgent                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Claude Agent SDK                                         │  │
│  │                                                          │  │
│  │  tools = [                                               │  │
│  │    FunctionTool(                                         │  │
│  │      name="fetch_ski_conditions",  # or notes tools      │  │
│  │      description="...",                                  │  │
│  │      input_schema={...},                                 │  │
│  │      function=_fetch_conditions                          │  │
│  │    ),                                                    │  │
│  │    ...                                                   │  │
│  │  ]                                                       │  │
│  │                                                          │  │
│  │  No external process, faster startup                     │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  SkiAgent:                                                    │
│    - Uses httpx for web fetching                              │
│    - Data source: cloudserv.skihood.com                       │
│    - Caches conditions data                                   │
│                                                               │
│  NotesAgent:                                                  │
│    - Local JSON storage in ~/.clarvis/notes/                  │
│    - Fuzzy matching for note names                            │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Adding a New Agent

### Step 1: Create Agent Directory

```
clarvis_agents/
└── my_agent/
    ├── __init__.py      # Exports: MyAgent, create_my_agent
    ├── agent.py         # MyAgent class implementing BaseAgent
    ├── config.py        # MyAgentConfig dataclass
    ├── prompts.py       # System prompts
    └── tools.py         # Native tools (if using SDK tools)
```

### Step 2: Implement BaseAgent

```python
# clarvis_agents/my_agent/agent.py
from clarvis_agents.core import BaseAgent, AgentCapability, AgentResponse, ConversationContext

class MyAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "my_agent"

    @property
    def description(self) -> str:
        return "Description for LLM routing context"

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="my_capability",
                description="What this capability does",
                keywords=["keyword1", "keyword2"],  # For fast-path routing
                examples=["example query 1", "example query 2"],  # For LLM routing
            ),
        ]

    async def process(self, query: str, context: Optional[ConversationContext] = None) -> AgentResponse:
        # Implement query processing
        return AgentResponse(
            content="Response text",
            success=True,
            agent_name=self.name,
        )

    def health_check(self) -> bool:
        # Return True if operational
        return True
```

### Step 3: Add to IntentClassifier

In `clarvis_agents/orchestrator/classifier.py`, add patterns:

```python
AGENT_PATTERNS: dict[str, dict[str, list[str]]] = {
    # ... existing agents ...
    "my_agent": {
        "keywords": ["keyword1", "keyword2", "keyword3"],
        "patterns": [
            r"\b(check|get)\b.*\b(my_thing)\b",
            r"\bmy_agent\b.*\b(action)\b",
        ],
    },
}
```

### Step 4: Register with Orchestrator

In `clarvis_agents/orchestrator/agent.py`, add to `create_orchestrator()`:

```python
try:
    from ..my_agent import MyAgent

    if issubclass(MyAgent, BaseAgent):
        from ..my_agent import create_my_agent

        my_agent = create_my_agent()
        registry.register(my_agent)
        logger.info("Registered My agent with orchestrator")
except (ImportError, TypeError):
    logger.debug("My agent not registered")
```

### Step 5: Add Routing Announcement

In `clarvis_agents/orchestrator/agent.py`:

```python
ROUTING_ANNOUNCEMENTS = {
    # ... existing announcements ...
    "my_agent": "Checking your thing. ",
}
```

### Step 6: Add Tests

Create `tests/test_my_agent/`:
- `test_agent.py` - Unit tests for MyAgent
- `test_config.py` - Configuration tests
- `test_tools.py` - Tool tests (if applicable)

## Configuration

### Orchestrator Config (`configs/orchestrator_config.json`)

```json
{
  "orchestrator": {
    "model": "claude-sonnet-4-20250514",
    "router_model": "claude-3-5-haiku-20241022",
    "session_timeout_minutes": 30,
    "max_turns": 5
  },
  "routing": {
    "code_routing_threshold": 0.7,
    "llm_routing_enabled": true,
    "follow_up_detection": true,
    "default_agent": null
  },
  "agents": {
    "gmail": { "enabled": true, "priority": 1 },
    "ski": { "enabled": true, "priority": 2 },
    "notes": { "enabled": true, "priority": 3 }
  }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `model` | claude-sonnet-4 | Model for direct responses |
| `router_model` | claude-3-5-haiku | Model for LLM routing (faster/cheaper) |
| `code_routing_threshold` | 0.7 | Confidence threshold for code-based routing |
| `llm_routing_enabled` | true | Enable LLM fallback routing |
| `follow_up_detection` | true | Detect and route follow-up queries |
| `session_timeout_minutes` | 30 | Session expiry time |

## API Endpoints

The orchestrator is exposed via the API server:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/query` | POST | Query the orchestrator (routes to appropriate agent) |
| `/api/v1/query/stream` | POST | Stream response via SSE |
| `/api/v1/agents` | GET | List available agents and their capabilities |

See `clarvis_agents/api/routes/orchestrator.py` for implementation details.
