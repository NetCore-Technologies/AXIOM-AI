from __future__ import annotations

import json
from pathlib import Path

import pytest

from axiom.core.roadmap import audit_roadmap


def _write_roadmap(path: Path, rows: list[str]) -> Path:
    path.write_text(
        "# Roadmap\n\n<!-- AXIOM-ROADMAP-UPDATE:START -->\n"
        "### 01 · Test group\n" + "\n".join(rows) +
        "\n<!-- AXIOM-ROADMAP-UPDATE:END -->\n",
        encoding="utf-8",
    )
    return path


def test_audit_parses_all_120_known_statuses_and_group_names(tmp_path: Path):
    rows = []
    for number in range(1, 121):
        status = "Implemented; tests passing" if number <= 30 else "In progress; validation pending" if number <= 50 else "Planned"
        rows.append(f"- [R{number:03d} · {status}] Example deliverable {number}.")
    report = audit_roadmap(_write_roadmap(tmp_path / "ROADMAP.md", rows))
    assert report["integrity"]["ok"] is True
    assert report["total"] == 120
    assert report["counts"] == {"implemented": 30, "in_progress": 20, "planned": 70, "unknown": 0}
    assert report["items"][0]["group"] == "Test group"
    assert report["items"][-1]["id"] == "R120"
    json.dumps(report)


def test_audit_reports_missing_duplicate_and_unknown_statuses(tmp_path: Path):
    rows = ["- [R001 · Implemented; tests passing] One", "- [R001 · Mystery] Duplicate"]
    report = audit_roadmap(_write_roadmap(tmp_path / "ROADMAP.md", rows))
    assert report["integrity"]["ok"] is False
    assert report["integrity"]["duplicate_ids"] == ["R001"]
    assert "R120" in report["integrity"]["missing_ids"]
    assert report["integrity"]["unknown_status_ids"] == ["R001"]


def test_audit_rejects_bad_markers_and_symlink(tmp_path: Path):
    bad = tmp_path / "ROADMAP.md"
    bad.write_text("# no markers", encoding="utf-8")
    with pytest.raises(ValueError, match="marker pair"):
        audit_roadmap(bad)
    link = tmp_path / "linked.md"
    try:
        link.symlink_to(bad)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="symbolic link"):
        audit_roadmap(link)


def test_audit_preserves_the_four_repository_status_classes(tmp_path: Path):
    rows = []
    for number in range(1, 121):
        if number <= 29:
            status = "Implemented; tests passing"
        elif number <= 51:
            status = "In progress; validation pending"
        elif number <= 119:
            status = "Planned"
        else:
            status = "In progress"
        rows.append(f"- [R{number:03d} · {status}] Item {number}")
    report = audit_roadmap(_write_roadmap(tmp_path / "ROADMAP.md", rows))
    assert report["integrity"]["ok"] is True
    assert report["counts"] == {"implemented": 29, "in_progress": 23, "planned": 68, "unknown": 0}


def test_roadmap_cli_emits_machine_readable_audit(tmp_path: Path):
    import typer
    from typer.testing import CliRunner

    from axiom.cli.roadmap import roadmap_app

    rows = [f"- [R{number:03d} · Planned] Item {number}" for number in range(1, 121)]
    source = _write_roadmap(tmp_path / "ROADMAP.md", rows)
    app = typer.Typer()
    app.add_typer(roadmap_app, name="roadmap")
    result = CliRunner().invoke(app, ["roadmap", "audit", "--path", str(source), "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["integrity"]["ok"] is True
    assert payload["total"] == 120
    assert payload["counts"]["planned"] == 120
