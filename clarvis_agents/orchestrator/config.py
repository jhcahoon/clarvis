"""Configuration for the orchestrator."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator agent."""

    model: str = "claude-sonnet-4-20250514"
    router_model: str = "claude-3-5-haiku-20241022"
    session_timeout_minutes: int = 30
    code_routing_threshold: float = 0.7
    llm_routing_enabled: bool = True
    follow_up_detection: bool = True

    @classmethod
    def from_file(cls, path: Path) -> "OrchestratorConfig":
        """Load configuration from a JSON file.

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

        return cls(
            model=data.get("model", "claude-sonnet-4-20250514"),
            router_model=data.get("router_model", "claude-3-5-haiku-20241022"),
            session_timeout_minutes=data.get("session_timeout_minutes", 30),
            code_routing_threshold=data.get("code_routing_threshold", 0.7),
            llm_routing_enabled=data.get("llm_routing_enabled", True),
            follow_up_detection=data.get("follow_up_detection", True),
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
