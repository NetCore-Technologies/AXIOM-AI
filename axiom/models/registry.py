import json
from dataclasses import asdict, dataclass
from pathlib import Path

from axiom.core.storage import atomic_write_text, file_lock


@dataclass
class Model:
    name: str
    source: str
    format: str = "unknown"
    parameters: str | None = None
    quantization: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise TypeError("Model name cannot be empty.")
        if not isinstance(self.source, str) or not self.source.strip():
            raise TypeError("Model source cannot be empty.")

    def to_dict(self) -> dict:
        return asdict(self)


class ModelRegistry:
    """Local AXIOM model registry."""

    def __init__(
        self,
        root: Path | None = None,
        *,
        create: bool = True,
    ):
        self.root = Path(root) if root is not None else Path(".axiom")
        self.registry_file = self.root / "models.json"
        self.lock_file = self.root / ".models.lock"

        if create:
            self.root.mkdir(parents=True, exist_ok=True)
            with file_lock(self.lock_file):
                if not self.registry_file.exists():
                    atomic_write_text(self.registry_file, "[]\n")

    def _read(self) -> list[Model]:
        if not self.registry_file.exists():
            return []
        if not self.registry_file.is_file():
            raise ValueError(
                f"Invalid model registry: expected a file at {self.registry_file}"
            )

        try:
            data = json.loads(self.registry_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid model registry: {self.registry_file}") from exc

        if not isinstance(data, list):
            raise ValueError(  # noqa: TRY004
                f"Invalid model registry: expected a JSON array in {self.registry_file}"
            )

        models: list[Model] = []
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"Invalid model registry entry at index {index}.")  # noqa: TRY004

            try:
                models.append(Model(**item))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid model registry entry at index {index}."
                ) from exc

        return models

    def list(self) -> list[Model]:
        return self._read()

    def add(self, model: Model) -> None:
        if not isinstance(model, Model):
            raise TypeError("model must be a Model instance.")

        self.root.mkdir(parents=True, exist_ok=True)
        with file_lock(self.lock_file):
            models = self._read()

            if any(existing.name == model.name for existing in models):
                raise ValueError(f"Model already exists: {model.name}")

            models.append(model)

            atomic_write_text(
                self.registry_file,
                json.dumps(
                    [item.to_dict() for item in models],
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
            )
