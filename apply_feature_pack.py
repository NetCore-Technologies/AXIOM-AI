#!/usr/bin/env python3
"""Apply the AXIOM diagnostics, roadmap audit, and support feature pack.

The script writes only new feature-pack files and performs strict, single-match
edits to existing files. It aborts before writing anything if any anchor is
missing or ambiguous. It does not contact GitHub, commit, push, or open a PR.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OVERLAY = HERE / "overlay"


class ApplyError(RuntimeError):
    pass


def _read(root: Path, path: str) -> str:
    target = root / path
    if not target.is_file() or target.is_symlink():
        raise ApplyError(f"Required regular file missing or unsafe: {path}")
    try:
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ApplyError(f"Could not read {path} as UTF-8: {type(exc).__name__}") from None


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ApplyError(f"Expected one edit anchor for {label}, found {count}; no files were changed.")
    return text.replace(old, new, 1)


def _replace_section(text: str, start: str, end: str, replacement: str, label: str) -> str:
    first = text.find(start)
    if first < 0 or text.find(start, first + len(start)) >= 0:
        raise ApplyError(f"Expected one start anchor for {label}; no files were changed.")
    last = text.find(end, first + len(start))
    if last < 0:
        raise ApplyError(f"Could not find end anchor for {label}; no files were changed.")
    return text[:first] + replacement + text[last:]


def _modified_sources(root: Path) -> dict[str, str]:
    sources = {
        "axiom/api/server.py": _read(root, "axiom/api/server.py"),
        "axiom/cli/extended.py": _read(root, "axiom/cli/extended.py"),
        "src/api/client.ts": _read(root, "src/api/client.ts"),
        "src/App.tsx": _read(root, "src/App.tsx"),
        "README.md": _read(root, "README.md"),
    }

    server = sources["axiom/api/server.py"]
    server = _replace_once(
        server,
        "from axiom.api.evaluation import router as evaluation_router\n",
        "from axiom.api.evaluation import router as evaluation_router\nfrom axiom.api.diagnostics import router as diagnostics_router\n",
        "API diagnostics router import",
    )
    server = _replace_once(
        server,
        "    app.include_router(evaluation_router)\n",
        "    app.include_router(evaluation_router)\n    app.include_router(diagnostics_router)\n",
        "API diagnostics router registration",
    )
    sources["axiom/api/server.py"] = server

    extended = sources["axiom/cli/extended.py"]
    extended = _replace_once(
        extended,
        "from axiom.daemon import local_summary\n",
        "from axiom.daemon import local_summary\nfrom axiom.core.diagnostics import diagnose_workspace\nfrom axiom.cli.support_bundle import register as register_support_bundle_cli\nfrom axiom.cli.roadmap import roadmap_app as roadmap_cli_app\n",
        "CLI diagnostics imports",
    )
    doctor_replacement = '''    @app.command("doctor")
    def doctor(
        json_output: bool = typer.Option(False, "--json", help="Emit stable machine-readable diagnostics."),
        workspace: str | None = typer.Option(None, "--workspace", help="Workspace directory to inspect."),
    ) -> None:
        """Inspect the current workspace, Python dependencies, and common tools."""
        try:
            report = diagnose_workspace(workspace)
        except (OSError, ValueError):
            message = {"schema_version": 1, "status": "error", "message": "Workspace could not be resolved safely."}
            typer.echo(json.dumps(message, sort_keys=True) if json_output else "Error: workspace could not be resolved safely.", err=not json_output)
            raise typer.Exit(code=2)
        tool_checks = [
            {"name": name, "available": bool(shutil.which(command)), "path": shutil.which(command)}
            for name, command in (("Python", "python3"), ("Python fallback", "python"), ("Git", "git"), ("Node.js", "node"), ("npm", "npm"))
        ]
        payload = {"schema_version": 1, "version": AXIOM_VERSION, "workspace": report, "tools": tool_checks}
        if json_output:
            typer.echo(json.dumps(payload, indent=2, sort_keys=True))
            if report["summary"]["failed"]:
                raise typer.Exit(code=1)
            return

        typer.echo(f"AXIOM Doctor — {AXIOM_VERSION}")
        typer.echo(f"Workspace: {report['workspace']['name']}")
        for check in report["checks"]:
            marker = "OK" if check["status"] == "pass" else "FAIL" if check["status"] == "fail" else "WARN" if check["status"] == "warn" else "INFO"
            typer.echo(f"[{marker:<4}] {check['title']}: {check['detail']}")
            if check["remediation"]:
                typer.echo(f"       Next: {check['remediation']}")
        for item in tool_checks:
            marker = "OK" if item["available"] else "WARN"
            typer.echo(f"[{marker:<4}] Tool {item['name']}: {item['path'] or 'not found'}")
        summary = report["summary"]
        typer.echo(f"Doctor complete: {summary['passed']} passed, {summary['warnings']} warning(s), {summary['failed']} failed")
        if summary["failed"]:
            raise typer.Exit(code=1)

'''
    extended = _replace_section(
        extended,
        '    @app.command("doctor")\n',
        '    @app.command("info")\n',
        doctor_replacement,
        "doctor command",
    )

    status_replacement = '''    @app.command("status")
    def status(
        json_output: bool = typer.Option(False, "--json", help="Emit stable machine-readable status."),
        workspace: str | None = typer.Option(None, "--workspace", help="Workspace directory to inspect."),
    ) -> None:
        """Show workspace health and local Git status without running jobs."""
        try:
            report = diagnose_workspace(workspace)
        except (OSError, ValueError):
            message = {"schema_version": 1, "status": "error", "message": "Workspace could not be resolved safely."}
            typer.echo(json.dumps(message, sort_keys=True) if json_output else "Error: workspace could not be resolved safely.", err=not json_output)
            raise typer.Exit(code=2)
        dirty = bool(git_output("status", "--porcelain"))
        payload = {
            "schema_version": 1,
            "version": AXIOM_VERSION,
            "workspace": report["workspace"],
            "health": {"status": report["status"], "summary": report["summary"]},
            "git": {
                "branch": git_output("branch", "--show-current") or None,
                "commit": git_output("rev-parse", "--short", "HEAD") or None,
                "dirty": dirty,
            },
        }
        if json_output:
            typer.echo(json.dumps(payload, indent=2, sort_keys=True))
            return

        table = Table(title="AXIOM STATUS")
        table.add_column("Item")
        table.add_column("Value")
        table.add_row("Version", AXIOM_VERSION)
        table.add_row("Workspace", report["workspace"]["name"])
        table.add_row("Project config", "found" if report["workspace"]["project_config_present"] else "not found")
        table.add_row("Workspace health", report["status"].upper())
        table.add_row("Checks", f"{report['summary']['passed']} passed / {report['summary']['warnings']} warnings / {report['summary']['failed']} failed")
        table.add_row("Git branch", payload["git"]["branch"] or "n/a")
        table.add_row("Git commit", payload["git"]["commit"] or "n/a")
        table.add_row("Working tree", "modified" if dirty else "clean")
        console.print(table)

'''
    extended = _replace_section(
        extended,
        '    @app.command("status")\n',
        '    @app.command("summary")\n',
        status_replacement,
        "status command",
    )

    config_replacement = '''    @config_app.command("validate")
    def config_validate(
        path: str = typer.Option("axiom.yaml", "--path", help="Path to a local axiom.yaml file"),
        json_output: bool = typer.Option(False, "--json", help="Emit a stable machine-readable result."),
    ) -> None:
        """Validate a local YAML mapping without echoing configuration values."""
        config = Path(path)
        status = "invalid"
        message = "Configuration validation failed."
        valid = False
        if config.is_symlink():
            message = "Configuration path must not be a symbolic link."
        elif not config.is_file():
            message = "Configuration file was not found."
        else:
            try:
                if config.stat().st_size > 256 * 1024:
                    raise ValueError("configuration exceeds the 256 KiB validation limit")
                contents = config.read_text(encoding="utf-8")
                parsed = yaml.safe_load(contents)
                if not contents.strip() or not isinstance(parsed, dict):
                    raise ValueError("configuration must be a non-empty YAML mapping")
                bad_sections = [key for key in ("project", "model", "dataset", "training", "evaluation", "deployment") if key in parsed and parsed[key] is not None and not isinstance(parsed[key], dict)]
                if bad_sections:
                    raise ValueError("known configuration sections must be YAML mappings")
            except (OSError, UnicodeError, yaml.YAMLError, ValueError):
                message = "Configuration could not be parsed as a bounded, compatible YAML mapping; values are withheld."
            else:
                valid = True
                status = "valid"
                message = "Configuration is valid YAML and known sections have compatible types."

        result = {"schema_version": 1, "status": status, "valid": valid, "path": str(config), "message": message}
        if json_output:
            typer.echo(json.dumps(result, indent=2, sort_keys=True))
        elif valid:
            console.print(f"[green]✓ {message}[/green]")
        else:
            console.print(f"[red]Error:[/red] {message}")
        if not valid:
            raise typer.Exit(code=1)

    app.add_typer(roadmap_cli_app, name="roadmap")
    register_support_bundle_cli(app)
'''
    config_start_marker = '    @config_app.command("validate")\n'
    if extended.count(config_start_marker) != 1:
        raise ApplyError("Expected one configuration validation section; no files were changed.")
    expected_tail = """        console.print(
            "[green]✓ axiom.yaml is valid YAML and contains a mapping.[/green]"
        )"""
    if not extended.rstrip().endswith(expected_tail):
        raise ApplyError("Configuration validation is no longer the final CLI registration block; refusing to discard later code.")
    config_start = extended.find(config_start_marker)
    extended = extended[:config_start] + config_replacement + "\n"
    sources["axiom/cli/extended.py"] = extended

    client = sources["src/api/client.ts"]
    type_anchor = "type ApiErrorBody = {\n"
    types = '''export type WorkspaceDiagnosticCheck = {
  id: string;
  title: string;
  status: "pass" | "warn" | "fail" | "info";
  severity: "info" | "warning" | "error";
  detail: string;
  remediation: string | null;
};

export type WorkspaceDiagnostics = {
  schema_version: number;
  generated_at: string;
  status: "pass" | "warn" | "fail";
  workspace: { name: string; project_config_present: boolean; is_project: boolean };
  summary: { passed: number; warnings: number; failed: number; informational: number; missing_dependencies: string[] };
  checks: WorkspaceDiagnosticCheck[];
};

'''
    client = _replace_once(client, type_anchor, types + type_anchor, "workspace diagnostic API types")
    roadmap_types = '''export type RoadmapAuditItem = {
  id: string;
  status: "implemented" | "in_progress" | "planned" | "unknown";
  status_label: string;
  title: string;
  group: string;
};

export type RoadmapAudit = {
  schema_version: number;
  generated_at: string;
  source: string;
  integrity: {
    ok: boolean;
    expected_items: number;
    parsed_items: number;
    missing_ids: string[];
    duplicate_ids: string[];
    unexpected_ids: string[];
    unknown_status_ids: string[];
  };
  total: number;
  counts: { implemented: number; in_progress: number; planned: number; unknown: number };
  items: RoadmapAuditItem[];
};

'''
    client = _replace_once(client, "type ApiErrorBody = {\n", roadmap_types + "type ApiErrorBody = {\n", "roadmap API types")
    runtime_anchor = '  runtime: () => requestJson<RuntimeSnapshot>("/api/workspace/runtime"),\n'
    api_methods = '''  workspaceDiagnostics: () => requestJson<WorkspaceDiagnostics>("/api/diagnostics/workspace"),

  roadmapAudit: () => requestJson<RoadmapAudit>("/api/diagnostics/roadmap"),

  downloadSupportBundle: async (): Promise<Blob> => {
    const requestId = globalThis.crypto?.randomUUID?.()
      ?? `ui-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15_000);
    try {
      const response = await fetch(`${API_BASE}/api/diagnostics/support-bundle`, {
        headers: { Accept: "application/zip", "X-Request-ID": requestId },
        signal: controller.signal,
        cache: "no-store",
      });
      if (!response.ok) {
        const raw = await response.text();
        let payload: unknown = raw;
        try { payload = raw ? JSON.parse(raw) as unknown : null; } catch { /* keep safe text fallback */ }
        const responseRequestId = response.headers.get("X-Request-ID") || requestId;
        throw new Error(`${messageFromPayload(payload, `Support bundle request failed (${response.status})`)} (request ID ${responseRequestId})`);
      }
      return await response.blob();
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        throw new Error(`Support bundle request timed out (request ID ${requestId}).`, { cause: error });
      }
      throw error;
    } finally {
      window.clearTimeout(timeout);
    }
  },

'''
    client = _replace_once(client, runtime_anchor, api_methods + runtime_anchor, "workspace diagnostics and support bundle API methods")
    sources["src/api/client.ts"] = client

    app_tsx = sources["src/App.tsx"]
    app_tsx = _replace_once(
        app_tsx,
        "  type WorkspaceEvent,\n",
        "  type WorkspaceEvent,\n  type WorkspaceDiagnostics,\n  type RoadmapAudit,\n",
        "GUI diagnostics type import",
    )
    app_tsx = _replace_once(
        app_tsx,
        "  const [datasetCount, setDatasetCount] = useState<number | null>(null);\n",
        "  const [datasetCount, setDatasetCount] = useState<number | null>(null);\n  const [workspaceDiagnostics, setWorkspaceDiagnostics] = useState<WorkspaceDiagnostics | null>(null);\n  const [bundleBusy, setBundleBusy] = useState(false);\n",
        "GUI diagnostics state",
    )
    download_function = '''
  const downloadBundle = async () => {
    setBundleBusy(true);
    try {
      const blob = await axiomApi.downloadSupportBundle();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "axiom-support-bundle.zip";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
      onNotify("Privacy-safe support bundle downloaded. Review it before sharing.", "success");
    } catch (cause) {
      onNotify(cause instanceof Error ? cause.message : "Could not download the support bundle.", "warning");
    } finally {
      setBundleBusy(false);
    }
  };
'''
    app_tsx = _replace_once(
        app_tsx,
        "  const runScan = async () => {\n",
        download_function + "\n  const runScan = async () => {\n",
        "GUI support bundle handler",
    )
    app_tsx = _replace_once(
        app_tsx,
        "      axiomApi.datasets(),\n    ]);\n",
        "      axiomApi.datasets(),\n      axiomApi.workspaceDiagnostics(),\n    ]);\n",
        "GUI diagnostics request",
    )
    # Correctly bind the fifth settled promise without disturbing the older states.
    app_tsx = _replace_once(
        app_tsx,
        "    const [healthResult, hardwareResult, modelResult, datasetResult] = await Promise.allSettled([",
        "    const [healthResult, hardwareResult, modelResult, datasetResult, workspaceDiagnosticsResult] = await Promise.allSettled([",
        "GUI diagnostics result tuple",
    )
    app_tsx = _replace_once(
        app_tsx,
        '    else { setDatasetCount(null); failures.push("dataset inventory"); }\n    setScanState',
        '    else { setDatasetCount(null); failures.push("dataset inventory"); }\n    if (workspaceDiagnosticsResult.status === "fulfilled") setWorkspaceDiagnostics(workspaceDiagnosticsResult.value);\n    else { setWorkspaceDiagnostics(null); failures.push("workspace diagnostics"); }\n    setScanState',
        "GUI diagnostics result handling",
    )
    old_header = '''  return <FeaturePage page="diagnostics" actions={<button type="button" className="button primary-button" onClick={() => void runScan()} disabled={scanState === "scanning"}><Wrench size={16} /> {scanState === "scanning" ? "Scanning…" : "Run diagnostics"}</button>}>
'''
    new_header = '''  return <FeaturePage page="diagnostics" actions={<>
    <button type="button" className="button secondary-button" onClick={() => void downloadBundle()} disabled={bundleBusy}><ArrowDownToLine size={16} /> {bundleBusy ? "Preparing bundle…" : "Download support bundle"}</button>
    <button type="button" className="button primary-button" onClick={() => void runScan()} disabled={scanState === "scanning"}><Wrench size={16} /> {scanState === "scanning" ? "Scanning…" : "Run diagnostics"}</button>
  </>}>
'''
    app_tsx = _replace_once(app_tsx, old_header, new_header, "GUI diagnostics page actions")
    diag_anchor = '''    </div>
    {!connected && scanState !== "scanning" && <Callout tone="warning" title="Start the local API">Open the AXIOM UI launcher or start the FastAPI service, then scan again.</Callout>}
'''
    diag_rows = '''    </div>
    {workspaceDiagnostics && <Surface title="Workspace checks" eyebrow="READ-ONLY BACKEND DIAGNOSTICS" action={<StatusPill tone={workspaceDiagnostics.status === "pass" ? "success" : workspaceDiagnostics.status === "fail" ? "danger" : "warning"}>{workspaceDiagnostics.status.toUpperCase()}</StatusPill>}>
      <p className="quiet-note">{workspaceDiagnostics.summary.passed} passed · {workspaceDiagnostics.summary.warnings} warning(s) · {workspaceDiagnostics.summary.failed} failed. Checks are read-only; no repair actions are run automatically.</p>
      <div className="diag-list">{workspaceDiagnostics.checks.map((check) => {
        const tone: Tone = check.status === "pass" ? "success" : check.status === "fail" ? "danger" : check.status === "warn" ? "warning" : "neutral";
        const Icon = check.status === "pass" ? CircleCheck : check.status === "fail" ? CircleAlert : TriangleAlert;
        return <DiagnosticRow key={check.id} icon={Icon} title={check.title} detail={`${check.detail}${check.remediation ? ` Next: ${check.remediation}` : ""}`} state={check.status.toUpperCase()} tone={tone} />;
      })}</div>
    </Surface>}
    {!connected && scanState !== "scanning" && <Callout tone="warning" title="Start the local API">Open the AXIOM UI launcher or start the FastAPI service, then scan again.</Callout>}
'''
    app_tsx = _replace_once(app_tsx, diag_anchor, diag_rows, "GUI workspace check list")
    app_tsx = _replace_once(app_tsx, '  | "diagnostics"\n  | "logs"\n', '  | "diagnostics"\n  | "roadmap"\n  | "logs"\n', "roadmap page type")
    nav_anchor = '''  {
    id: "diagnostics",
    label: "Diagnostics",
    description: "Health and configuration",
    icon: Wrench,
  },
'''
    nav_new = nav_anchor + '''  {
    id: "roadmap",
    label: "Roadmap",
    description: "Scoped feature status and integrity",
    icon: FileCode2,
  },
'''
    app_tsx = _replace_once(app_tsx, nav_anchor, nav_new, "roadmap navigation item")
    meta_anchor = '''  diagnostics: {
    label: "Diagnostics",
    kicker: "OBSERVABILITY",
    description: "Find configuration drift and local blockers before they become confusing failures.",
  },
'''
    meta_new = meta_anchor + '''  roadmap: {
    label: "Roadmap",
    kicker: "DELIVERY STATUS / R001–R120",
    description: "Read the source roadmap, inspect unchecked work, and verify the 120-item scope without guessing status.",
  },
'''
    app_tsx = _replace_once(app_tsx, meta_anchor, meta_new, "roadmap page metadata")
    switch_anchor = '''    case "diagnostics":
      return <Diagnostics onNotify={onNotify} />;
'''
    app_tsx = _replace_once(app_tsx, switch_anchor, '''    case "roadmap":
      return <RoadmapPage />;
''' + switch_anchor, "roadmap page switch")
    roadmap_component = '''function RoadmapPage() {
  const [report, setReport] = useState<RoadmapAudit | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "open" | "implemented">("all");

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      setReport(await axiomApi.roadmapAudit());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load the roadmap audit.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void refresh(); }, []);
  const normalizedQuery = query.trim().toLowerCase();
  const visibleItems = (report?.items ?? []).filter((item) => {
    const matchesQuery = !normalizedQuery || `${item.id} ${item.title} ${item.group} ${item.status_label}`.toLowerCase().includes(normalizedQuery);
    const matchesStatus = filter === "all" || (filter === "implemented" ? item.status === "implemented" : item.status !== "implemented");
    return matchesQuery && matchesStatus;
  });

  return <FeaturePage page="roadmap" actions={<button type="button" className="button secondary-button" onClick={() => void refresh()} disabled={loading}><RefreshCcw size={16} /> {loading ? "Auditing…" : "Refresh roadmap"}</button>}>
    {error && <InlineAlert tone="warning" role="alert">{error}</InlineAlert>}
    {report && <div className="summary-grid">
      <SummaryCard icon={Check} label="Implemented" value={String(report.counts.implemented)} detail="Source roadmap marks these as tested" tone={report.counts.implemented === 120 ? "success" : "neutral"} />
      <SummaryCard icon={Clock3} label="In progress" value={String(report.counts.in_progress)} detail="Validation or implementation remains" tone={report.counts.in_progress ? "warning" : "success"} />
      <SummaryCard icon={CircleAlert} label="Planned" value={String(report.counts.planned)} detail="Not marked as delivered" tone={report.counts.planned ? "warning" : "success"} />
      <SummaryCard icon={FileCode2} label="Scope integrity" value={report.integrity.ok ? `${report.total}/120` : "REVIEW"} detail={report.integrity.ok ? "IDs are complete and unique" : "Missing, duplicate, or unknown roadmap entries"} tone={report.integrity.ok ? "success" : "danger"} />
    </div>}
    {report && <Surface title="Scoped product roadmap" eyebrow="SOURCE-OF-TRUTH STATUS">
      <p className="quiet-note">Statuses are read from ROADMAP.md and are not inferred from file presence. {report.counts.implemented} of {report.total} entries are currently marked “Implemented; tests passing”.</p>
      {!report.integrity.ok && <Callout tone="warning" title="Roadmap integrity needs review">Missing IDs: {report.integrity.missing_ids.join(", ") || "none"}. Duplicates: {report.integrity.duplicate_ids.join(", ") || "none"}. Unknown statuses: {report.integrity.unknown_status_ids.join(", ") || "none"}.</Callout>}
      <label className="event-filter"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter by ID, title, group, or status" aria-label="Search roadmap items" /></label>
      <div className="segmented-control" role="group" aria-label="Roadmap status filter">
        <button type="button" className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>All</button>
        <button type="button" className={filter === "open" ? "active" : ""} onClick={() => setFilter("open")}>Open work</button>
        <button type="button" className={filter === "implemented" ? "active" : ""} onClick={() => setFilter("implemented")}>Implemented</button>
      </div>
      {loading ? <div className="loading-state" role="status">Reading ROADMAP.md…</div> : <div className="event-list">{visibleItems.map((item) => {
        const tone: Tone = item.status === "implemented" ? "success" : item.status === "in_progress" ? "warning" : item.status === "unknown" ? "danger" : "neutral";
        return <div className="event-row" key={item.id}><span className="event-marker" /><div><b>{item.id} · {item.title}</b><small>{item.group} · {item.status_label}</small></div><StatusPill tone={tone}>{item.status_label.toUpperCase()}</StatusPill></div>;
      })}{visibleItems.length === 0 && <EmptyState icon={Search} title="No roadmap items match" description="Change the search or status filter to see more entries." />}</div>}
      <p className="quiet-note">Showing {visibleItems.length} of {report.total} source entries · generated {formatTimestamp(report.generated_at)}.</p>
    </Surface>}
  </FeaturePage>;
}

'''
    app_tsx = _replace_once(app_tsx, "function LogsPage() {\n", roadmap_component + "function LogsPage() {\n", "roadmap page component")
    sources["src/App.tsx"] = app_tsx

    readme = sources["README.md"]
    if readme.lstrip().startswith("# AXIOM-AI roadmap feature pack"):
        raise ApplyError("README.md contains the feature-pack README, not the AXIOM project README. Restore the project README before applying; no files were changed.")
    docs_reference = "\n## Diagnostics, roadmap audit, and support bundles\n\nRun `axiom doctor --json` for machine-readable diagnostics, `axiom roadmap audit --json` to validate the 120 roadmap IDs and status roll-up, or `axiom support-bundle --output ./axiom-support-bundle.zip` to export a privacy-minimized support archive. The archive excludes configuration values, environment variables, credentials, model weights, datasets, logs, and absolute paths. The Control Center Roadmap page reads statuses directly from `ROADMAP.md`. Inspect support bundles before sharing. See [the diagnostics and support guide](docs/Diagnostics-and-Support.md).\n"
    if "## Diagnostics, roadmap audit, and support bundles" not in readme:
        readme = readme.rstrip() + "\n" + docs_reference
    sources["README.md"] = readme
    return sources


def _copy_overlay(root: Path) -> list[str]:
    additions = [
        "axiom/core/diagnostics.py",
        "axiom/api/diagnostics.py",
        "axiom/core/roadmap.py",
        "axiom/cli/roadmap.py",
        "axiom/cli/support_bundle.py",
        "tests/test_workspace_diagnostics.py",
        "tests/test_workspace_diagnostics_api.py",
        "tests/test_roadmap_audit.py",
        "docs/Diagnostics-and-Support.md",
    ]
    for relative in additions:
        source = OVERLAY / relative
        destination = root / relative
        if not source.is_file():
            raise ApplyError(f"Feature pack is missing {relative}.")
        if destination.exists() or destination.is_symlink():
            current_hash = hashlib.sha256(destination.read_bytes()).hexdigest() if destination.is_file() and not destination.is_symlink() else None
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            if current_hash == source_hash:
                continue
            raise ApplyError(f"Refusing to overwrite existing project file: {relative}")
    return additions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path, help="Path to a local AXIOM-AI checkout")
    parser.add_argument("--check-only", action="store_true", help="Check all anchors without writing files")
    args = parser.parse_args()
    root = args.repository.expanduser().resolve()
    if not (root / ".git").exists() or not (root / "ROADMAP.md").is_file():
        print("Error: repository must be a Git checkout containing ROADMAP.md.", file=sys.stderr)
        return 2
    try:
        sources = _modified_sources(root)
        additions = _copy_overlay(root)
        if args.check_only:
            print("All existing-file anchors matched; no files were written.")
            print(f"New files prepared: {len(additions)}")
            return 0
        # All anchor and overwrite checks finish before any write happens.
        for relative, content in sources.items():
            target = root / relative
            target.write_text(content, encoding="utf-8", newline="\n")
        for relative in additions:
            source = OVERLAY / relative
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copyfile(source, destination)
        print("Applied local AXIOM diagnostics, roadmap audit, and support changes. No GitHub write was performed.")
        print("Next: run the full Python suite, npm run lint, npm run build, and Playwright E2E before reviewing a diff.")
        print("Roadmap statuses were intentionally not changed because full release gates remain unverified.")
        return 0
    except ApplyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Error while applying feature pack: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
