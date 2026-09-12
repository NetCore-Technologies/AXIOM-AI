from dataclasses import dataclass, asdict
from pathlib import Path
import json


@dataclass
class Model:
    name: str
    source: str
    format: str = "unknown"
    parameters: str | None = None
    quantization: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class ModelRegistry:
    """Local AXIOM model registry."""

    def __init__(self, root: Path | None = None):
        self.root = root or Path(".axiom")
        self.root.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.root / "models.json"

        if not self.registry_file.exists():
            self.registry_file.write_text("[]", encoding="utf-8")

    def list(self) -> list[Model]:
        data = json.loads(self.registry_file.read_text(encoding="utf-8"))
        return [Model(**item) for item in data]

    def add(self, model: Model) -> None:
        models = self.list()

        if any(existing.name == model.name for existing in models):
            raise ValueError(f"Model already exists: {model.name}")

        models.append(model)

        self.registry_file.write_text(
            json.dumps(
                [model.to_dict() for model in models],
                indent=2,
            ),
            encoding="utf-8",
        )
