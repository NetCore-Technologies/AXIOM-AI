from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

import axiom.cli.main as cli_main
from axiom.cli.main import app
from axiom.models.registry import Model, ModelRegistry


runner = CliRunner()


def test_model_list_json_has_stable_schema_and_empty_behavior(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    registry = ModelRegistry()
    registry.add(Model(name="tiny-llama", source="/models/tiny-llama", format="safetensors"))

    result = runner.invoke(app, ["model", "list", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["total"] == 1
    assert payload["models"][0]["name"] == "tiny-llama"

    empty_dir = tmp_path / "empty-project"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)
    result = runner.invoke(app, ["model", "list", "--json"])
    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout)["models"] == []


def test_model_info_json_is_bounded_and_does_not_download_weights(monkeypatch) -> None:
    def fake_model_info(*, repo_id: str, files_metadata: bool):
        assert files_metadata is True
        return SimpleNamespace(
            id=repo_id,
            author="org",
            library_name="transformers",
            pipeline_tag="text-generation",
            downloads=12,
            likes=3,
            gated=False,
            private=False,
            tags=["llama", "text-generation"],
            siblings=[
                SimpleNamespace(rfilename="model.safetensors"),
                SimpleNamespace(rfilename="model.gguf"),
            ],
        )

    monkeypatch.setattr(cli_main, "HfApi", lambda: SimpleNamespace(model_info=fake_model_info))
    result = runner.invoke(app, ["model", "info", "org/tiny", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["model"]["id"] == "org/tiny"
    assert payload["model"]["formats"] == ["GGUF", "Safetensors"]
    assert payload["model"]["files"]["total"] == 2
    assert payload["model"]["files"]["truncated"] is False
    assert "no model weights were downloaded" in payload["scope_note"].lower()


def test_model_inspect_json_reports_local_capabilities(tmp_path: Path) -> None:
    model = tmp_path / "tiny-llama"
    model.mkdir()
    (model / "config.json").write_text(
        json.dumps({"model_type": "llama", "architectures": ["LlamaForCausalLM"]}),
        encoding="utf-8",
    )
    (model / "tokenizer.json").write_text("{}", encoding="utf-8")
    (model / "model.safetensors").write_bytes(b"metadata inspection fixture")

    result = runner.invoke(app, ["model", "inspect", str(model), "--json"])

    assert result.exit_code == 0, result.stdout
    inspection = json.loads(result.stdout)["inspection"]
    assert inspection["path"] == str(model.resolve())
    assert inspection["model_type"] == "llama"
    assert inspection["has_safetensors"] is True
    assert "Text generation" in inspection["capabilities"]


def test_dataset_inspect_validate_and_stats_share_json_shape(tmp_path: Path) -> None:
    dataset = tmp_path / "train.jsonl"
    dataset.write_text(
        '{"text":"first"}\n'
        'not-json\n'
        '\n',
        encoding="utf-8",
    )

    inspect = runner.invoke(app, ["dataset", "inspect", str(dataset), "--json"])
    stats = runner.invoke(app, ["dataset", "stats", str(dataset), "--json"])
    validate = runner.invoke(app, ["dataset", "validate", str(dataset), "--json"])

    assert inspect.exit_code == 0, inspect.stdout
    assert stats.exit_code == 0, stats.stdout
    assert validate.exit_code == 1, validate.stdout
    reports = [json.loads(result.stdout) for result in (inspect, stats, validate)]
    assert all(payload["schema_version"] == 1 for payload in reports)
    assert all(payload["dataset"]["invalid"] == 1 for payload in reports)
    assert all(payload["dataset"]["errors"][0]["line"] == 2 for payload in reports)


def test_integration_list_json_returns_empty_or_registered_records(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["integration", "list", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["total"] == 0
    assert payload["integrations"] == []


def test_model_search_json_skips_symlink_entries(tmp_path: Path) -> None:
    root = tmp_path / "models"
    model_dir = root / "tiny-llama"
    model_dir.mkdir(parents=True)
    (model_dir / "weights.safetensors").write_bytes(b"weights")
    outside = tmp_path / "private.safetensors"
    outside.write_bytes(b"private")
    linked = root / "linked-llama.safetensors"
    try:
        linked.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        # The non-symlink match still confirms the output shape on platforms
        # where symlinks are not permitted by the current user.
        linked = None

    result = runner.invoke(app, ["model", "search", "llama", "--path", str(root), "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["total"] >= 1
    assert all("path" in item and "kind" in item and "size_bytes" in item for item in payload["matches"])
    assert all("private.safetensors" not in item["path"] for item in payload["matches"])



def test_model_analyze_json_reports_metadata_and_estimate_basis(tmp_path: Path, monkeypatch) -> None:
    config = {
        "model_type": "llama",
        "architectures": ["LlamaForCausalLM"],
        "hidden_size": 8,
        "intermediate_size": 12,
        "num_hidden_layers": 1,
        "num_attention_heads": 2,
        "num_key_value_heads": 1,
        "vocab_size": 16,
        "max_position_embeddings": 128,
        "torch_dtype": "bfloat16",
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    def fake_model_info(*, repo_id: str, files_metadata: bool):
        assert files_metadata is True
        return SimpleNamespace(
            id=repo_id,
            siblings=[
                SimpleNamespace(rfilename="config.json", size=512),
                SimpleNamespace(rfilename="model.safetensors", size=4096),
            ],
        )

    monkeypatch.setattr(cli_main, "HfApi", lambda: SimpleNamespace(
        model_info=fake_model_info,
        hf_hub_download=lambda *, repo_id, filename: str(config_path),
    ))
    result = runner.invoke(app, ["model", "analyze", "org/tiny", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    analysis = payload["analysis"]
    assert payload["schema_version"] == 1
    assert analysis["repo_id"] == "org/tiny"
    assert analysis["architecture"] == "LlamaForCausalLM"
    assert analysis["context_length"] == 128
    assert analysis["parameter_source"] == "architecture estimate"
    assert analysis["files"]["items"] == ["config.json", "model.safetensors"]
    assert "no model weights were downloaded" in payload["scope_note"].lower()


def test_system_info_json_reports_hardware_and_fit_scope(monkeypatch) -> None:
    hardware = SimpleNamespace(
        os_name="Linux",
        architecture="x86_64",
        cpu_cores=8,
        ram_gb=16.0,
        gpu_name="Test GPU",
        vram_gb=8.0,
        cuda_available=True,
    )
    monkeypatch.setattr(cli_main, "detect_hardware", lambda: hardware)
    monkeypatch.setattr(cli_main, "estimate_model_fit", lambda billions, _hardware: f"fit-{billions}B")

    result = runner.invoke(app, ["system", "info", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["hardware"]["gpu_name"] == "Test GPU"
    assert payload["hardware"]["vram_gb"] == 8.0
    assert len(payload["model_fit_estimates"]) == 7
    assert payload["model_fit_estimates"][0]["assessment"] == "fit-1B"
    assert "not measured runtime capacity" in payload["fit_scope_note"]
