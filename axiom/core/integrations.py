from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json


class IntegrationType(str, Enum):
    MCP = "mcp"
    CLI = "cli"
    HTTP = "http"
    A2A = "a2a"


@dataclass
class AgentIntegration:
    name: str
    type: IntegrationType
    command: str | None = None
    url: str | None = None
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type.value,
            "command": self.command,
            "url": self.url,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentIntegration":
        return cls(
            name=data["name"],
            type=IntegrationType(data["type"]),
            command=data.get("command"),
            url=data.get("url"),
            description=data.get("description", ""),
        )


class IntegrationRegistry:
    """Local registry for external AI-agent integrations."""

    def __init__(self, root: Path | None = None):
        self.root = root or Path(".axiom")
        self.root.mkdir(parents=True, exist_ok=True)

        self.path = self.root / "integrations.json"

        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def list(self) -> list[AgentIntegration]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [AgentIntegration.from_dict(item) for item in data]

    def add(self, integration: AgentIntegration) -> None:
        integrations = self.list()

        if any(
            item.name.lower() == integration.name.lower()
            for item in integrations
        ):
            raise ValueError(
                f"Integration already exists: {integration.name}"
            )

        integrations.append(integration)

        self.path.write_text(
            json.dumps(
                [item.to_dict() for item in integrations],
                indent=2,
            ),
            encoding="utf-8",
        )

    def remove(self, name: str) -> bool:
        integrations = self.list()

        remaining = [
            item
            for item in integrations
            if item.name.lower() != name.lower()
        ]

        if len(remaining) == len(integrations):
            return False

        self.path.write_text(
            json.dumps(
                [item.to_dict() for item in remaining],
                indent=2,
            ),
            encoding="utf-8",
        )

        return True
