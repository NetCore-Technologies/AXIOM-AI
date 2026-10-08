import json
from http.client import HTTPConnection
from pathlib import Path

import pytest

from axiom.daemon import serve_in_thread, validate_bind_host


def get_json(host: str, port: int, path: str) -> tuple[int, dict]:
    connection = HTTPConnection(host, port, timeout=2)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        return response.status, payload
    finally:
        connection.close()


@pytest.fixture()
def daemon_server():
    server, thread = serve_in_thread()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_daemon_chooses_an_available_loopback_port(daemon_server):
    host, port = daemon_server.server_address[:2]

    assert host == "127.0.0.1"
    assert port > 0

    status, payload = get_json(host, port, "/health")

    assert status == 200
    assert payload["name"] == "AXIOM"
    assert payload["status"] == "ok"
    assert payload["version"]


def test_daemon_info_describes_the_local_capabilities(daemon_server, tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "axiom.yaml").write_text("name: local\n", encoding="utf-8")
    host, port = daemon_server.server_address[:2]

    status, payload = get_json(host, port, "/api/info")

    assert status == 200
    assert payload["service"] == "local-daemon"
    assert payload["port"] == port
    assert payload["project_config"] is True
    assert "model-inspection" in payload["capabilities"]


def test_daemon_returns_a_small_not_found_payload(daemon_server):
    host, port = daemon_server.server_address[:2]

    status, payload = get_json(host, port, "/does-not-exist")

    assert status == 404
    assert payload["error"] == "not_found"
    assert payload["hint"] == "Try /health or /api/info."


def test_daemon_rejects_non_loopback_hosts_by_default():
    with pytest.raises(ValueError, match="local-only"):
        validate_bind_host("0.0.0.0")

    assert validate_bind_host("0.0.0.0", allow_network=True) == "0.0.0.0"
