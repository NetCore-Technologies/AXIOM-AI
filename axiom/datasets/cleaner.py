from __future__ import annotations

import json
import os
import tempfile
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


class DatasetPathError(OSError):
    """Raised when a cleaning destination would violate source safety."""


def _reject_non_json_constant(value: str) -> None:
    raise ValueError(f"Non-standard JSON constant: {value}")


def _same_path(source: Path, destination: Path) -> bool:
    try:
        if destination.exists() and os.path.samefile(source, destination):
            return True
    except OSError:
        __import__("logging").getLogger(__name__).debug("intentionally ignored exception", exc_info=True)

    return source.resolve(strict=False) == destination.resolve(strict=False)


def clean_jsonl(
    source: Path,
    output: Path,
) -> DatasetCleaningResult:
    source = Path(source)
    output = Path(output)

    if not source.is_file():
        raise FileNotFoundError(f"Dataset not found: {source}")

    if output.exists() and output.is_dir():
        raise IsADirectoryError(f"Output path is a directory: {output}")

    if _same_path(source, output):
        raise DatasetPathError(
            "Output path must differ from the source dataset; "
            "cleaning in place is not supported."
        )

    seen: set[str] = set()

    total_lines = 0
    kept = 0
    removed_invalid = 0
    removed_empty = 0
    removed_duplicates = 0
    removed_schema = 0

    expected_fields: set[str] | None = None

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    file_descriptor: int | None = None

    try:
        with source.open("r", encoding="utf-8") as infile:
            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{output.name}.",
                suffix=".tmp",
                dir=output.parent,
            )
            outfile = os.fdopen(
                file_descriptor,
                "w",
                encoding="utf-8",
                newline="\n",
            )
            file_descriptor = None

            with outfile:
                for raw_line in infile:
                    total_lines += 1
                    line = raw_line.strip()

                    if not line:
                        removed_empty += 1
                        continue

                    try:
                        item: Any = json.loads(
                            line,
                            parse_constant=_reject_non_json_constant,
                        )
                    except (json.JSONDecodeError, ValueError):
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

                outfile.flush()
                os.fsync(outfile.fileno())

        os.replace(temporary_name, output)
        temporary_name = None
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                __import__("logging").getLogger(__name__).debug("intentionally ignored exception", exc_info=True)

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
