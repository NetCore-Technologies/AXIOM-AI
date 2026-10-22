from __future__ import annotations

import json

import pytest

from axiom.core.engine import (
    _inspect_model_config,
    _resolve_model_directory,
    validate_generation,
)


def test_validate_generation_accepts_bounded_local_prompt() -> None:
    assert validate_generation("hello", 32, 0.7) == ("hello", 32, 0.7)
    assert validate_generation("hello", 1, 0) == ("hello", 1, 0.0)


@pytest.mark.parametrize(
    ("prompt", "tokens", "temperature"),
    [
        (" ", 1, 0.7),
        ("x" * 12_001, 1, 0.7),
        ("hello", 0, 0.7),
        ("hello", 2_049, 0.7),
        ("hello", 32, -0.1),
        ("hello", 32, 2.1),
        ("hello", True, 0.7),
    ],
)
def test_validate_generation_rejects_invalid_bounds(prompt, tokens, temperature) -> None:
    with pytest.raises(ValueError):
        validate_generation(prompt, tokens, temperature)


def test_model_config_is_read_only_and_reports_architecture(tmp_path) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"model_type": "llama", "architectures": ["LlamaForCausalLM"]}),
        encoding="utf-8",
    )
    inspected = _inspect_model_config(tmp_path)
    assert inspected["model_type"] == "llama"
    assert inspected["architecture"] == "LlamaForCausalLM"


def test_model_config_rejects_missing_model_type(tmp_path) -> None:
    (tmp_path / "config.json").write_text(json.dumps({"hidden_size": 8}), encoding="utf-8")
    with pytest.raises(ValueError, match="model_type"):
        _inspect_model_config(tmp_path)


def test_model_directory_must_exist_and_be_a_directory(tmp_path) -> None:
    file_path = tmp_path / "model.txt"
    file_path.write_text("not a model", encoding="utf-8")
    with pytest.raises(ValueError):
        _resolve_model_directory(str(file_path), "Base model")
