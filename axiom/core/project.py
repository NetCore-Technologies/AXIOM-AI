from pathlib import Path

DEFAULT_CONFIG = """\
project:
  name: {name}
  version: 0.1.0

model:
  base: null
  source: null

dataset:
  source: null
  format: jsonl

training:
  method: null
  epochs: 1
  learning_rate: null

evaluation:
  enabled: true

deployment:
  target: local
"""


def create_project(name: str, directory: Path | None = None) -> Path:
    if not name.strip():
        raise ValueError("Project name cannot be empty.")

    root = (directory or Path.cwd()) / name

    if root.exists():
        raise FileExistsError(f"Project already exists: {root}")

    directories = [
        root / "data" / "raw",
        root / "data" / "processed",
        root / "models",
        root / "experiments",
        root / "evaluations",
        root / "outputs",
    ]

    for directory_path in directories:
        directory_path.mkdir(parents=True, exist_ok=True)

    (root / "axiom.yaml").write_text(
        DEFAULT_CONFIG.format(name=name),
        encoding="utf-8",
    )

    (root / "README.md").write_text(
        f"# {name}\n\n"
        "AI project created with AXIOM.\n",
        encoding="utf-8",
    )

    return root
