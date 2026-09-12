from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


class DatasetInspection:
    def __init__(
        self,
        path: Path,
        format: str,
        samples: int,
        valid: int,
        invalid: int,
        empty: int,
        duplicates: int,
        fields: list[str],
        estimated_tokens: int,
    ):
        self.path = path
        self.format = format
        self.samples = samples
        self.valid = valid
        self.invalid = invalid
        self.empty = empty
        self.duplicates = duplicates
        self.fields = fields
        self.estimated_tokens = estimated_tokens


def _estimate_tokens(value: Any) -> int:
    """Cheap token estimate for first-pass dataset analysis."""
    text = json.dumps(value, ensure_ascii=False)
    return max(1, len(text) // 4)


def inspect_jsonl(path: Path) -> DatasetInspection:
    total = 0
    valid = 0
    invalid = 0
    empty = 0
    token_estimate = 0
    field_counter: Counter[str] = Counter()
    fingerprints: Counter[str] = Counter()

    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            total += 1
            line = raw_line.strip()

            if not line:
                empty += 1
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                invalid += 1
                continue

            valid += 1
            token_estimate += _estimate_tokens(item)

            if isinstance(item, dict):
                field_counter.update(item.keys())

            fingerprints.update([json.dumps(item, sort_keys=True, ensure_ascii=False)])

    duplicates = sum(count - 1 for count in fingerprints.values() if count > 1)

    return DatasetInspection(
        path=path,
        format="jsonl",
        samples=total,
        valid=valid,
        invalid=invalid,
        empty=empty,
        duplicates=duplicates,
        fields=sorted(field_counter),
        estimated_tokens=token_estimate,
    )


def inspect_dataset(path: str) -> DatasetInspection:
    dataset_path = Path(path)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    if not dataset_path.is_file():
        raise ValueError(f"Dataset path is not a file: {dataset_path}")

    suffix = dataset_path.suffix.lower()

    if suffix == ".jsonl":
        return inspect_jsonl(dataset_path)

    raise ValueError(
        f"Unsupported dataset format: {suffix or 'unknown'}. "
        "Currently supported: .jsonl"
    )
