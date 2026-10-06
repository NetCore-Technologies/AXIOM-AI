from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DatasetCleaningResult:
    def __init__(
        self,
        source: Path,
        output: Path,
        total_lines: int,
        kept: int,
        removed_invalid: int,
        removed_empty: int,
        removed_duplicates: int,
        removed_schema: int,
    ):
        self.source = source
        self.output = output
        self.total_lines = total_lines
        self.kept = kept
        self.removed_invalid = removed_invalid
        self.removed_empty = removed_empty
        self.removed_duplicates = removed_duplicates
        self.removed_schema = removed_schema


def clean_jsonl(
    source: Path,
    output: Path,
) -> DatasetCleaningResult:
    seen: set[str] = set()

    total_lines = 0
    kept = 0
    removed_invalid = 0
    removed_empty = 0
    removed_duplicates = 0
    removed_schema = 0

    expected_fields: set[str] | None = None

    output.parent.mkdir(parents=True, exist_ok=True)

    with source.open("r", encoding="utf-8") as infile, output.open(
        "w", encoding="utf-8"
    ) as outfile:
        for raw_line in infile:
            total_lines += 1
            line = raw_line.strip()

            if not line:
                removed_empty += 1
                continue

            try:
                item: Any = json.loads(line)
            except json.JSONDecodeError:
                removed_invalid += 1
                continue

            if not isinstance(item, dict):
                removed_schema += 1
                continue

            fields = set(item.keys())

            if expected_fields is None:
                expected_fields = fields
            elif fields != expected_fields:
                removed_schema += 1
                continue

            fingerprint = json.dumps(
                item,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            )

            if fingerprint in seen:
                removed_duplicates += 1
                continue

            seen.add(fingerprint)

            outfile.write(
                json.dumps(
                    item,
                    ensure_ascii=False,
                )
                + "\n"
            )

            kept += 1

    return DatasetCleaningResult(
        source=source,
        output=output,
        total_lines=total_lines,
        kept=kept,
        removed_invalid=removed_invalid,
        removed_empty=removed_empty,
        removed_duplicates=removed_duplicates,
        removed_schema=removed_schema,
    )
