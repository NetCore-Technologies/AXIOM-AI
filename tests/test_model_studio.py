from __future__ import annotations
import json
import pytest
from axiom.core import model_studio as studio

def test_model_identifiers_and_files_are_validated():
    assert studio.validate_ollama_name("qwen3.5:0.8b") == "qwen3.5:0.8b"
    assert studio.validate_repo_id("example/tiny-gguf") == "example/tiny-gguf"
    assert studio.validate_gguf_filename("model-Q4_K_M.gguf") == "model-Q4_K_M.gguf"
    for value in ("https://example.com/model", "../model", "/tmp/model"):
        with pytest.raises(ValueError): studio.validate_ollama_name(value)
    for value in ("owner", "owner/../private", "https://example.com/a/b"):
        with pytest.raises(ValueError): studio.validate_repo_id(value)
    for value in ("../model.gguf", "folder/model.gguf", "model.safetensors", "https://host/file.gguf"):
        with pytest.raises(ValueError): studio.validate_gguf_filename(value)

def test_search_uses_fixed_public_catalogue_and_filters_gguf(monkeypatch):
    seen = {}
    def fake(url, timeout=12.0):
        seen["url"] = url
        return [
            {"id":"example/model-GGUF", "tags":["gguf","text-generation"],"downloads":100,"likes":4,"lastModified":"2026-01-01"},
            {"id":"example/not-related", "tags":["text-generation"],"downloads":200},
        ]
    monkeypatch.setattr(studio, "_read_public_json", fake)
    result = studio.search_gguf_catalog("test model", 5)
    assert "https://huggingface.co/api/models?" in seen["url"]
    assert result["count"] == 1
    assert result["results"][0]["id"] == "example/model-GGUF"

def test_files_only_returns_single_file_gguf(monkeypatch):
    monkeypatch.setattr(studio, "_read_public_json", lambda *_args, **_kwargs: {"siblings":[
        {"rfilename":"model-Q4_K_M.gguf","size":123},
        {"rfilename":"tokenizer.json"},
        {"rfilename":"subdir/shard.gguf"},
    ]})
    result = studio.list_gguf_files("example/model")
    assert result["count"] == 1
    assert result["files"][0]["filename"] == "model-Q4_K_M.gguf"
    assert result["files"][0]["size_bytes"] == 123

def test_empty_search_is_rejected_without_network(monkeypatch):
    monkeypatch.setattr(studio, "_read_public_json", lambda *_a, **_k: pytest.fail("must not make request"))
    with pytest.raises(ValueError): studio.search_gguf_catalog("  ")

def test_remote_ollama_host_is_rejected(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "https://models.example.net")
    with pytest.raises(studio.ModelStudioError, match="non-loopback"):
        studio._require_loopback_ollama()
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    studio._require_loopback_ollama()

def test_remote_provider_requires_public_https_and_rejects_private_addresses(monkeypatch):
    import socket
    monkeypatch.setattr(studio.socket, "getaddrinfo", lambda *_a, **_k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    assert studio.validate_remote_base_url("https://provider.example/api/v1") == "https://provider.example/api/v1"
    with pytest.raises(ValueError, match="HTTPS"):
        studio.validate_remote_base_url("http://provider.example/v1")
    monkeypatch.setattr(studio.socket, "getaddrinfo", lambda *_a, **_k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ValueError, match="public IP"):
        studio.validate_remote_base_url("https://provider.example/v1")
