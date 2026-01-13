"""Configuration for the orchestrator."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator agent."""

    # Orchestrator settings
    model: str = "claude-sonnet-4-20250514"
    router_model: str = "claude-3-5-haiku-20241022"
    session_timeout_minutes: int = 30
    max_turns: int = 5

    # Routing settings
    code_routing_threshold: float = 0.7
    llm_routing_enabled: bool = True
    follow_up_detection: bool = True
    default_agent: Optional[str] = None

    # Agent settings
    enabled_agents: Dict[str, bool] = field(default_factory=lambda: {"gmail": True})
    agent_priorities: Dict[str, int] = field(default_factory=lambda: {"gmail": 1})

    # Logging settings
    log_level: str = "INFO"
    log_routing_decisions: bool = True
    log_agent_responses: bool = True

    @classmethod
    def from_file(cls, path: Path) -> "OrchestratorConfig":
        """Load configuration from a JSON file.

        Supports both nested structure (new format) and flat structure (legacy).
        Nested format has sections: orchestrator, routing, agents, logging.
        Flat format has all fields at the root level.

        Args:
            path: Path to the configuration file.

        Returns:
            OrchestratorConfig instance with values from file,
            falling back to defaults for missing fields.
        """
        if not path.exists():
            return cls()

        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            # Return defaults if config file is corrupted or unreadable
            return cls()

        # Detect nested vs flat structure
        is_nested = any(
            key in data for key in ("orchestrator", "routing", "agents", "logging")
        )

        if is_nested:
            return cls._from_nested(data)
        else:
            return cls._from_flat(data)

    @classmethod
    def _from_flat(cls, data: dict) -> "OrchestratorConfig":
        """Parse flat (legacy) config format."""
        return cls(
            model=data.get("model", "claude-sonnet-4-20250514"),
            router_model=data.get("router_model", "claude-3-5-haiku-20241022"),
            session_timeout_minutes=data.get("session_timeout_minutes", 30),
            max_turns=data.get("max_turns", 5),
            code_routing_threshold=data.get("code_routing_threshold", 0.7),
            llm_routing_enabled=data.get("llm_routing_enabled", True),
            follow_up_detection=data.get("follow_up_detection", True),
            default_agent=data.get("default_agent"),
            enabled_agents=data.get("enabled_agents", {"gmail": True}),
            agent_priorities=data.get("agent_priorities", {"gmail": 1}),
            log_level=data.get("log_level", "INFO"),
            log_routing_decisions=data.get("log_routing_decisions", True),
            log_agent_responses=data.get("log_agent_responses", True),
        )

    @classmethod
    def _from_nested(cls, data: dict) -> "OrchestratorConfig":
        """Parse nested config format with orchestrator/routing/agents/logging sections."""
        orch = data.get("orchestrator", {})
        routing = data.get("routing", {})
        agents_section = data.get("agents", {})
        logging_section = data.get("logging", {})

        # Parse agents section into enabled_agents and agent_priorities
        enabled_agents: Dict[str, bool] = {}
        agent_priorities: Dict[str, int] = {}

        for agent_name, agent_config in agents_section.items():
            if isinstance(agent_config, dict):
                enabled_agents[agent_name] = agent_config.get("enabled", False)
                agent_priorities[agent_name] = agent_config.get("priority", 99)

        # Use defaults if no agents configured
        if not enabled_agents:
            enabled_agents = {"gmail": True}
        if not agent_priorities:
            agent_priorities = {"gmail": 1}

        return cls(
            # Orchestrator settings
            model=orch.get("model", "claude-sonnet-4-20250514"),
            router_model=orch.get("router_model", "claude-3-5-haiku-20241022"),
            session_timeout_minutes=orch.get("session_timeout_minutes", 30),
            max_turns=orch.get("max_turns", 5),
            # Routing settings
            code_routing_threshold=routing.get("code_routing_threshold", 0.7),
            llm_routing_enabled=routing.get("llm_routing_enabled", True),
            follow_up_detection=routing.get("follow_up_detection", True),
            default_agent=routing.get("default_agent"),
            # Agent settings
            enabled_agents=enabled_agents,
            agent_priorities=agent_priorities,
            # Logging settings
            log_level=logging_section.get("level", "INFO"),
            log_routing_decisions=logging_section.get("log_routing_decisions", True),
            log_agent_responses=logging_section.get("log_agent_responses", True),
        )

    @classmethod
    def default_config_path(cls) -> Path:
        """Return the default configuration file path."""
        return (
            Path(__file__).parent.parent.parent / "configs" / "orchestrator_config.json"
        )


def load_config() -> OrchestratorConfig:
    """Load the orchestrator configuration from the default path."""
    return OrchestratorConfig.from_file(OrchestratorConfig.default_config_path())
