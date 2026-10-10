#!/usr/bin/env python3
"""Safely install AXIOM's JSONL dataset profiler into an existing checkout.

Run from the AXIOM repository root:
    python3 /path/to/axiom_add_dataset_profiler.py

The script is idempotent, writes backups before modifying existing files, and
fails without applying partial changes when expected source anchors are absent.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
from pathlib import Path

PROFILER = r'''"""Bounded, local-first profiling for JSONL datasets.

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
'''

UI_TYPES = '''type DatasetProfileField = {
  name: string;
  occurrences: number;
  null_count: number;
  null_rate: number;
  types: Record<string, number>;
  possibly_sensitive: boolean;
};

type DatasetProfileReport = {
  file_name: string;
  file_size_bytes: number;
  bytes_scanned: number;
  lines_scanned: number;
  valid_rows: number;
  invalid_rows: number;
  empty_rows: number;
  duplicate_rows: number;
  overlong_rows: number;
  privacy_review_recommended: boolean;
  possibly_sensitive_fields: string[];
  truncated: boolean;
  fields: DatasetProfileField[];
  warnings: string[];
};

'''

UI_COMPONENT = r'''function Datasets({ onNotify }: { onNotify: (message: string, tone?: Tone) => void }) {
  const [datasets, setDatasets] = useState<Array<{ path: string }>>([]);
  const [profile, setProfile] = useState<DatasetProfileReport | null>(null);
  const [profileBusy, setProfileBusy] = useState<string | null>(null);
  const [inventoryBusy, setInventoryBusy] = useState(false);

  const refresh = async () => {
    setInventoryBusy(true);
    try {
      const response = await fetch(`${API_BASE}/api/files?kind=datasets`);
      const data = await response.json() as { items?: Array<{ path: string }>; message?: string };
      if (!response.ok) throw new Error(data.message || "Could not load datasets");
      setDatasets(Array.isArray(data.items) ? data.items : []);
    } catch (error: unknown) {
      onNotify(error instanceof Error ? error.message : "Dataset inventory unavailable", "warning");
    } finally {
      setInventoryBusy(false);
    }
  };

  useEffect(() => { void refresh(); }, []);

  const runProfile = async (path: string) => {
    setProfileBusy(path);
    try {
      const query = new URLSearchParams({ path });
      const response = await fetch(`${API_BASE}/api/dataset/profile?${query.toString()}`);
      const data = await response.json() as { profile?: DatasetProfileReport; message?: string };
      if (!response.ok || !data.profile) throw new Error(data.message || "Dataset profiling failed");
      setProfile(data.profile);
      onNotify(`Profile ready: ${data.profile.valid_rows.toLocaleString()} valid rows.`);
    } catch (error: unknown) {
      onNotify(error instanceof Error ? error.message : "Dataset profiling failed", "warning");
    } finally {
      setProfileBusy(null);
    }
  };

  return <FeaturePage page="datasets" actions={<button type="button" className="button primary-button" onClick={() => backendAction("datasets.import", onNotify, "Dataset import requested. Add a JSONL file under the workspace, then refresh.")}><Plus size={16} /> Import dataset</button>}>
    <div className="info-grid">
      <InfoCard icon={Database} label="Datasets" value={`${datasets.length}`} detail={datasets.length ? "JSONL files found" : "No JSONL files"} tone={datasets.length ? "success" : "neutral"} />
      <InfoCard icon={CircleAlert} label="Profiler" value="Local" detail="Structural checks only" tone="success" />
      <InfoCard icon={BarChart3} label="Privacy review" value={profile?.privacy_review_recommended ? "Recommended" : "On demand"} detail="Sensitive-looking field names" tone={profile?.privacy_review_recommended ? "warning" : "neutral"} />
    </div>
    <Surface title="Dataset workspace" eyebrow="INSPECTION QUEUE" action={<button type="button" className="icon-text-button" onClick={() => { void refresh(); }} disabled={inventoryBusy}><RefreshCcw size={15} /> {inventoryBusy ? "Refreshing" : "Refresh"}</button>}>
      {datasets.length ? <div className="module-list">{datasets.map((dataset) => <div className="module-row" key={dataset.path}>
        <span className="module-icon"><Database size={17} /></span>
        <span className="module-copy"><b>{dataset.path}</b><small>JSONL dataset · local workspace</small></span>
        <button type="button" className="button secondary-button" disabled={profileBusy !== null} onClick={() => { void runProfile(dataset.path); }}>{profileBusy === dataset.path ? "Profiling…" : "Profile"}</button>
      </div>)}</div> : <EmptyState icon={Database} title="No dataset report yet" description="Add a JSONL file inside the AXIOM workspace, then refresh this view." action={<CliReference command="axiom dataset inspect ./data/train.jsonl" />} />}
    </Surface>
    {profile && <Surface title={`Profile: ${profile.file_name}`} eyebrow="JSONL STRUCTURE REPORT" action={<button type="button" className="icon-text-button" onClick={() => setProfile(null)}>Clear report</button>}>
      <div className="info-grid">
        <InfoCard icon={Database} label="Valid rows" value={profile.valid_rows.toLocaleString()} detail="JSON object rows" tone="success" />
        <InfoCard icon={CircleAlert} label="Invalid rows" value={profile.invalid_rows.toLocaleString()} detail={`${profile.empty_rows} blank · ${profile.overlong_rows} oversized`} tone={profile.invalid_rows ? "warning" : "neutral"} />
        <InfoCard icon={RefreshCcw} label="Duplicates" value={profile.duplicate_rows.toLocaleString()} detail="Repeated valid rows" tone={profile.duplicate_rows ? "warning" : "neutral"} />
      </div>
      <p className="quiet-note">Scanned {profile.bytes_scanned.toLocaleString()} of {profile.file_size_bytes.toLocaleString()} bytes across {profile.lines_scanned.toLocaleString()} lines{profile.truncated ? " · Partial report: a scan limit was reached" : " · Complete scan"}.</p>
      {profile.privacy_review_recommended && <p className="quiet-note">Privacy review recommended for field names: {profile.possibly_sensitive_fields.join(", ")}. AXIOM does not display their values.</p>}
      {profile.warnings.map((warning) => <p className="quiet-note" key={warning}>{warning}</p>)}
      <div className="module-list">{profile.fields.map((field) => <div className="module-row" key={field.name}>
        <span className="module-icon"><BarChart3 size={17} /></span>
        <span className="module-copy"><b>{field.name}{field.possibly_sensitive ? " · review" : ""}</b><small>{field.occurrences} values · {field.null_count} null · types: {Object.entries(field.types).map(([kind, count]) => `${kind} ${count}`).join(", ")}</small></span>
        <small>{(field.null_rate * 100).toFixed(1)}% null</small>
      </div>)}</div>
    </Surface>}
    <ContractNote command="axiom dataset validate ./data/train.jsonl" />
  </FeaturePage>;
}

'''

TEST_PROFILER = r'''import json

from axiom.datasets.profiler import profile_jsonl


def test_profile_counts_rows_duplicates_and_types(tmp_path):
    source = tmp_path / "train.jsonl"
    source.write_text(
        '{"text":"hello","count":1}\n'
        '{"text":"hello","count":1}\n'
        '{"text":"world","count":null}\n'
        'not json\n'
        '\n',
        encoding="utf-8",
    )

    report = profile_jsonl(source)
    assert report["valid_rows"] == 3
    assert report["invalid_rows"] == 1
    assert report["empty_rows"] == 1
    assert report["duplicate_rows"] == 1
    fields = {field["name"]: field for field in report["fields"]}
    assert fields["count"]["null_count"] == 1
    assert fields["text"]["types"] == {"string": 3}


def test_profile_flags_sensitive_field_names_without_exposing_values(tmp_path):
    secret_value = "private-test-value-98765"
    source = tmp_path / "private.jsonl"
    source.write_text(json.dumps({"email": secret_value, "password_hash": "hash"}) + "\n", encoding="utf-8")

    report = profile_jsonl(source)
    rendered = json.dumps(report)
    assert report["privacy_review_recommended"] is True
    assert set(report["possibly_sensitive_fields"]) == {"email", "password_hash"}
    assert secret_value not in rendered


def test_profile_enforces_byte_and_line_limits(tmp_path):
    source = tmp_path / "large.jsonl"
    source.write_text('{"text":"' + ('x' * 256) + '"}\n{"text":"later"}\n', encoding="utf-8")

    report = profile_jsonl(source, max_bytes=32, max_rows=100, max_line_bytes=16)
    assert report["truncated"] is True
    assert report["bytes_scanned"] <= 32
    assert report["overlong_rows"] >= 1 or report["invalid_rows"] >= 1


def test_profile_rejects_invalid_limits_and_non_object_json(tmp_path):
    source = tmp_path / "mixed.jsonl"
    source.write_text('[1,2]\nnull\nNaN\n', encoding="utf-8")
    report = profile_jsonl(source)
    assert report["valid_rows"] == 0
    assert report["invalid_rows"] == 3

    try:
        profile_jsonl(source, max_rows=0)
    except ValueError as exc:
        assert "positive integers" in str(exc)
    else:
        raise AssertionError("invalid limit should be rejected")
'''

TEST_API = r'''from http import HTTPStatus

from axiom.daemon_api import route


def test_dataset_profile_api_returns_report_without_raw_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    (data / "train.jsonl").write_text(
        '{"text":"hello"}\n'
        '{"text":"hello"}\n'
        '{"email":"private-value"}\n'
        'invalid json\n',
        encoding="utf-8",
    )

    status, payload = route("/api/dataset/profile", {"path": ["data/train.jsonl"]})
    assert status == HTTPStatus.OK
    report = payload["profile"]
    assert report["valid_rows"] == 3
    assert report["invalid_rows"] == 1
    assert report["duplicate_rows"] == 1
    assert report["privacy_review_recommended"] is True
    assert "private-value" not in repr(payload)


def test_dataset_profile_api_rejects_wrong_extension(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.txt").write_text('{"text":"x"}\n', encoding="utf-8")
    status, payload = route("/api/dataset/profile", {"path": ["data.txt"]})
    assert status == HTTPStatus.UNPROCESSABLE_ENTITY
    assert payload["error"] == "unsupported_format"


def test_dataset_profile_api_rejects_outside_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    status, payload = route("/api/dataset/profile", {"path": ["../outside.jsonl"]})
    assert status == HTTPStatus.BAD_REQUEST
    assert payload["error"] == "invalid_path"
'''

ROADMAP_BLOCK = '''\n<!-- AXIOM_DATASET_PROFILER_BEGIN -->
### Dataset profiler — implemented foundation
- [x] Bounded JSONL row/field profiling endpoint (`/api/dataset/profile`)
- [x] Duplicate, malformed-row, null-rate, and field-type statistics
- [x] Sensitive-looking field-name warnings without returning row values
- [x] Existing Datasets page integration and automated tests
- [ ] Broader privacy analysis and configurable retention/report export
<!-- AXIOM_DATASET_PROFILER_END -->\n'''


def fail(message: str) -> None:
    raise RuntimeError(message)


def backup(path: Path, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / path.relative_to(Path.cwd())
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="AXIOM repository root (default: current directory)")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    required = (root / "axiom/daemon_api.py", root / "src/App.tsx", root / "tests")
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        print("ERROR: Not an AXIOM repository root; missing: " + ", ".join(missing), file=sys.stderr)
        return 2

    daemon_path = root / "axiom/daemon_api.py"
    app_path = root / "src/App.tsx"
    roadmap_path = root / "docs/ROADMAP.md"
    daemon = daemon_path.read_text(encoding="utf-8")
    app = app_path.read_text(encoding="utf-8")

    # Prepare/validate every patch in memory first so an anchor failure is non-destructive.
    if "# AXIOM_DATASET_PROFILE_IMPORT" not in daemon:
        import_anchor = "from axiom.datasets.inspector import inspect_dataset\n"
        if import_anchor not in daemon:
            fail(f"Cannot find import anchor in {daemon_path}; no files changed.")
        daemon = daemon.replace(
            import_anchor,
            import_anchor + "# AXIOM_DATASET_PROFILE_IMPORT\nfrom axiom.datasets.profiler import profile_jsonl\n",
            1,
        )

    if "# AXIOM_DATASET_PROFILE_ENDPOINT" not in daemon:
        route_anchor = '''        if path == "/api/dataset/inspect":
            target = resolve_in_workspace(_first(query, "path"))
            inspection = inspect_dataset(str(target))
            return HTTPStatus.OK, {"inspection": _jsonable(vars(inspection))}
'''
        if route_anchor not in daemon:
            fail(f"Cannot find dataset inspection route in {daemon_path}; no files changed.")
        route_addition = route_anchor + '''
        # AXIOM_DATASET_PROFILE_ENDPOINT
        if path == "/api/dataset/profile":
            target = resolve_in_workspace(_first(query, "path"))
            if target.suffix.lower() != ".jsonl":
                return _error(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    "unsupported_format",
                    "Dataset profiling currently supports .jsonl files.",
                )
            report = profile_jsonl(target)
            return HTTPStatus.OK, {"profile": report}
'''
        daemon = daemon.replace(route_anchor, route_addition, 1)

    if '"/api/dataset/profile"' not in daemon.split("API_PATHS:", 1)[-1]:
        paths_anchor = '    "/api/dataset/inspect",\n'
        if paths_anchor not in daemon:
            fail(f"Cannot find API_PATHS dataset anchor in {daemon_path}; no files changed.")
        daemon = daemon.replace(paths_anchor, paths_anchor + '    "/api/dataset/profile",\n', 1)

    if "AXIOM_DATASET_PROFILE_UI" not in app:
        start = app.find("function Datasets(")
        end = app.find("function Training(", start + 1)
        if start < 0 or end < 0:
            fail(f"Cannot locate Datasets component boundary in {app_path}; no files changed.")
        component = UI_TYPES + "// AXIOM_DATASET_PROFILE_UI\n" + UI_COMPONENT
        app = app[:start] + component + app[end:]

    changes: dict[Path, str] = {
        daemon_path: daemon,
        app_path: app,
        root / "axiom/datasets/profiler.py": PROFILER,
        root / "tests/test_dataset_profiler.py": TEST_PROFILER,
        root / "tests/test_dataset_profiler_api.py": TEST_API,
    }
    if roadmap_path.exists():
        roadmap = roadmap_path.read_text(encoding="utf-8")
        if "AXIOM_DATASET_PROFILER_BEGIN" not in roadmap:
            changes[roadmap_path] = roadmap.rstrip() + "\n\n" + ROADMAP_BLOCK

    # Compile-check the Python code before touching the checkout.
    compile(PROFILER, "axiom/datasets/profiler.py", "exec")
    compile(TEST_PROFILER, "tests/test_dataset_profiler.py", "exec")
    compile(TEST_API, "tests/test_dataset_profiler_api.py", "exec")

    backup_root = root / ".axiom" / "patch-backups" / (
        "dataset-profiler-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    already_current = True
    for path, content in changes.items():
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            already_current = False
            break
    if already_current:
        print("Dataset profiler is already installed; no changes needed.")
        return 0

    for path, content in changes.items():
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        if path.exists():
            backup(path, backup_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    print("Installed dataset profiler changes:")
    for path in changes:
        print("  " + str(path.relative_to(root)))
    print("Backups of modified files: " + str(backup_root.relative_to(root)))
    print("\nNext run:")
    print("  python3 -m pytest -q tests/test_dataset_profiler.py tests/test_dataset_profiler_api.py tests/test_daemon_api.py")
    print("  npm run build")
    print("  npm run lint")
    print("\nNo commits, pushes, release tags, or package publication were performed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
