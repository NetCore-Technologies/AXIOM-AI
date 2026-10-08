from pathlib import Path

import pytest

from axiom.optimizer.model import create_runtime_bundle


def _model_root(tmp_path: Path) -> Path:
    root = tmp_path / "models" / "safe-model"
    root.mkdir(parents=True)
    (root / "config.json").write_text("{}", encoding="utf-8")
    return root


def test_runtime_bundle_rejects_source_symlinks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    model = _model_root(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("not model data", encoding="utf-8")
    (model / "tokenizer.json").symlink_to(outside)

    with pytest.raises(ValueError, match="unsupported symlink"):
        create_runtime_bundle(str(model), ".axiom/optimized/bundle")


def test_runtime_bundle_rejects_destination_symlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    model = _model_root(tmp_path)
    (model / "nested").mkdir()
    (model / "nested" / "config.json").write_text("{}", encoding="utf-8")
    output = tmp_path / ".axiom" / "optimized" / "bundle"
    output.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (output / "nested").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="destination escapes"):
        create_runtime_bundle(str(model), str(output))
