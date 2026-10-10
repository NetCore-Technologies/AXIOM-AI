"""Bounded, local-first profiling for JSONL datasets.

The profiler reports structural metadata only. It never returns raw row values.
Callers handling user-supplied paths should validate workspace containment first.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_MAX_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_ROWS = 100_000
DEFAULT_MAX_LINE_BYTES = 1024 * 1024
MAX_TRACKED_FIELDS = 500
MAX_FIELD_NAME_LENGTH = 160

SENSITIVE_FIELD_PATTERNS = (
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "access_key", "authorization", "email", "phone", "mobile", "address",
    "ssn", "social_security", "credit_card", "card_number", "date_of_birth",
    "birth_date", "cookie",
)


def _reject_non_json_constant(value: str) -> None:
    """Reject NaN and Infinity, which are not standard JSON values."""
    raise ValueError(f"Non-standard JSON constant: {value}")


def _value_type(value: Any) -> str:
    """Return a stable JSON-oriented type label."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def _field_looks_sensitive(name: str) -> bool:
    """Flag likely sensitive field names, not field contents."""
    normalized = name.casefold().replace("-", "_").replace(" ", "_")
    return any(pattern in normalized for pattern in SENSITIVE_FIELD_PATTERNS)


def _display_field_name(name: str) -> str:
    """Bound the size of names returned in reports."""
    if len(name) <= MAX_FIELD_NAME_LENGTH:
        return name
    return name[: MAX_FIELD_NAME_LENGTH - 1] + "…"


def _canonical_fingerprint(row: dict[str, Any]) -> str:
    """Hash a canonical representation without returning or persisting it."""
    canonical = json.dumps(
        row, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def profile_jsonl(
    path: str | Path,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_rows: int = DEFAULT_MAX_ROWS,
    max_line_bytes: int = DEFAULT_MAX_LINE_BYTES,
) -> dict[str, Any]:
    """Profile a JSONL file with bounded streaming reads.

    `path` must already be checked for workspace containment by any API caller.
    Only structural metadata and likely-sensitive field names are returned.
    """
    if any(type(v) is not int or v < 1 for v in (max_bytes, max_rows, max_line_bytes)):
        raise ValueError("Profiling limits must be positive integers.")

    source = Path(path).expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError("Dataset path must refer to a regular file.")

    file_size = source.stat().st_size
    bytes_read = lines_scanned = valid_rows = invalid_rows = 0
    empty_rows = overlong_rows = duplicate_rows = omitted_field_count = 0
    truncated = False
    fingerprints: set[str] = set()
    field_occurrences: Counter[str] = Counter()
    field_nulls: Counter[str] = Counter()
    field_types: dict[str, Counter[str]] = {}

    with source.open("rb") as stream:
        while lines_scanned < max_rows:
            remaining = max_bytes - bytes_read
            if remaining <= 0:
                truncated = True
                break

            raw_line = stream.readline(min(max_line_bytes + 1, remaining + 1))
            if not raw_line:
                break
            if len(raw_line) > remaining:
                bytes_read = max_bytes
                truncated = True
                break

            bytes_read += len(raw_line)
            lines_scanned += 1

            if len(raw_line) > max_line_bytes:
                invalid_rows += 1
                overlong_rows += 1
                # Discard the rest of an oversized line using bounded chunks.
                while not raw_line.endswith(b"\n"):
                    remaining = max_bytes - bytes_read
                    if remaining <= 0:
                        truncated = True
                        break
                    chunk = stream.readline(min(65_536, remaining + 1))
                    if not chunk:
                        break
                    if len(chunk) > remaining:
                        bytes_read = max_bytes
                        truncated = True
                        break
                    bytes_read += len(chunk)
                    raw_line = chunk
                if truncated:
                    break
                continue

            stripped = raw_line.strip()
            if not stripped:
                empty_rows += 1
                continue

            try:
                row = json.loads(
                    stripped.decode("utf-8"),
                    parse_constant=_reject_non_json_constant,
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                invalid_rows += 1
                continue
            if not isinstance(row, dict):
                invalid_rows += 1
                continue

            valid_rows += 1
            fingerprint = _canonical_fingerprint(row)
            if fingerprint in fingerprints:
                duplicate_rows += 1
            else:
                fingerprints.add(fingerprint)

            for raw_name, value in row.items():
                name = str(raw_name)
                if name not in field_occurrences and len(field_occurrences) >= MAX_TRACKED_FIELDS:
                    omitted_field_count += 1
                    continue
                field_occurrences[name] += 1
                if value is None:
                    field_nulls[name] += 1
                field_types.setdefault(name, Counter())[_value_type(value)] += 1

    if bytes_read < file_size and (lines_scanned >= max_rows or bytes_read >= max_bytes):
        truncated = True

    fields = []
    for name in sorted(field_occurrences):
        count = field_occurrences[name]
        null_count = field_nulls[name]
        fields.append({
            "name": _display_field_name(name),
            "occurrences": count,
            "null_count": null_count,
            "null_rate": round(null_count / count, 4) if count else 0.0,
            "types": dict(sorted(field_types[name].items())),
            "possibly_sensitive": _field_looks_sensitive(name),
        })

    sensitive_fields = [field["name"] for field in fields if field["possibly_sensitive"]]
    warnings: list[str] = []
    if invalid_rows:
        warnings.append("Some rows are invalid or have unsupported structure.")
    if duplicate_rows:
        warnings.append("Duplicate valid rows were detected.")
    if sensitive_fields:
        warnings.append("Some field names may indicate sensitive data; review locally before sharing.")
    if truncated:
        warnings.append("The profile is partial because a configured scanning limit was reached.")
    if omitted_field_count:
        warnings.append("Some field occurrences were omitted after the field tracking limit.")

    return {
        "format": "jsonl",
        "file_name": source.name,
        "file_size_bytes": file_size,
        "bytes_scanned": bytes_read,
        "lines_scanned": lines_scanned,
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "empty_rows": empty_rows,
        "duplicate_rows": duplicate_rows,
        "overlong_rows": overlong_rows,
        "unique_fields_tracked": len(fields),
        "omitted_field_occurrences": omitted_field_count,
        "possibly_sensitive_fields": sensitive_fields,
        "privacy_review_recommended": bool(sensitive_fields),
        "truncated": truncated,
        "fields": fields,
        "warnings": warnings,
        "limits": {"max_bytes": max_bytes, "max_rows": max_rows, "max_line_bytes": max_line_bytes},
    }
