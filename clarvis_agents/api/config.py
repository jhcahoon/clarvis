"""Configuration for Clarvis API server."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class AgentConfig:
    """Configuration for an individual agent."""

    enabled: bool = True
    timeout_seconds: int = 120


@dataclass
class ServerConfig:
    """Configuration for the API server."""

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    debug: bool = False


@dataclass
class APIConfig:
    """Configuration for the Clarvis API."""

    server: ServerConfig = field(default_factory=ServerConfig)
    agents: Dict[str, AgentConfig] = field(default_factory=dict)

    @classmethod
    def from_file(cls, config_path: Path) -> "APIConfig":
        """
        Load configuration from a JSON file.

        Args:
            config_path: Path to the configuration file

        Returns:
            APIConfig instance
        """
        if not config_path.exists():
            return cls()

        with open(config_path) as f:
            data = json.load(f)

        server_data = data.get("server", {})
        server = ServerConfig(
            host=server_data.get("host", "0.0.0.0"),
            port=server_data.get("port", 8000),
            cors_origins=server_data.get("cors_origins", ["*"]),
            debug=server_data.get("debug", False),
        )

        agents = {}
        for name, agent_data in data.get("agents", {}).items():
            agents[name] = AgentConfig(
                enabled=agent_data.get("enabled", True),
                timeout_seconds=agent_data.get("timeout_seconds", 120),
            )

        return cls(server=server, agents=agents)

    @classmethod
    def default_config_path(cls) -> Path:
        """Return the default configuration file path."""
        return Path(__file__).parent.parent.parent / "configs" / "api_config.json"


def load_config() -> APIConfig:
    """Load the API configuration from the default path."""
    return APIConfig.from_file(APIConfig.default_config_path())
