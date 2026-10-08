"""Small, local-only HTTP daemon for the AXIOM CLI.

The daemon is intentionally dependency-free. It gives local scripts and future
integrations a stable health/info boundary without turning AXIOM into a hosted
service.
"""

from __future__ import annotations

import ipaddress
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any, TextIO
from urllib.parse import urlsplit

from axiom.version import __version__

LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def validate_bind_host(host: str, *, allow_network: bool = False) -> str:
    """Validate a daemon bind address before opening a listening socket."""

    normalized = host.strip()
    if not normalized:
        raise ValueError("host cannot be empty")

    is_loopback = normalized.lower() in LOOPBACK_HOSTS
    if not is_loopback:
        try:
            is_loopback = ipaddress.ip_address(normalized).is_loopback
        except ValueError:
            is_loopback = False

    if not is_loopback and not allow_network:
        raise ValueError(
            "AXIOM daemon is local-only by default; use a loopback host "
            "or pass --allow-network explicitly"
        )

    return normalized


def _display_url(host: str, port: int) -> str:
    display_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"http://{display_host}:{port}"


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")


class _DaemonServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], request_handler: type[BaseHTTPRequestHandler]):
        super().__init__(server_address, request_handler)
        self.axion_host = server_address[0]


class _RequestHandler(BaseHTTPRequestHandler):
    server: _DaemonServer

    protocol_version = "HTTP/1.1"

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlsplit(self.path).path.rstrip("/") or "/"

        if path == "/":
            self._send_json(
                HTTPStatus.OK,
                {
                    "name": "AXIOM",
                    "service": "local-daemon",
                    "message": "AXIOM is ready for local model, dataset, and hardware workflows.",
                    "health": "/health",
                    "info": "/api/info",
                },
            )
            return

        if path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {"name": "AXIOM", "status": "ok", "version": __version__},
            )
            return

        if path == "/api/info":
            cwd = Path.cwd()
            self._send_json(
                HTTPStatus.OK,
                {
                    "name": "AXIOM",
                    "version": __version__,
                    "service": "local-daemon",
                    "host": self.server.axion_host,
                    "port": self.server.server_address[1],
                    "working_directory": str(cwd),
                    "project_config": (cwd / "axiom.yaml").is_file(),
                    "capabilities": [
                        "project-scaffolding",
                        "model-inspection",
                        "dataset-validation",
                        "hardware-detection",
                        "training-plans",
                    ],
                },
            )
            return

        self._send_json(
            HTTPStatus.NOT_FOUND,
            {"error": "not_found", "path": path, "hint": "Try /health or /api/info."},
        )

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlsplit(self.path).path.rstrip("/") or "/"
        if path in {"/", "/health", "/api/info"}:
            self.send_response(HTTPStatus.OK)
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, _format: str, *_args: object) -> None:
        # The CLI owns the one useful startup line; request logs would make the
        # daemon noisy when it is used from a terminal or a supervisor.
        return


def start_daemon(
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    allow_network: bool = False,
) -> ThreadingHTTPServer:
    """Create a daemon server without starting its serving thread.

    ``port=0`` asks the operating system for a currently available port. The
    returned server is useful to callers that want to manage its lifecycle or
    run it in a background thread.
    """

    if not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")

    normalized_host = validate_bind_host(host, allow_network=allow_network)
    return _DaemonServer((normalized_host, port), _RequestHandler)


def daemon_url(server: ThreadingHTTPServer) -> str:
    """Return the URL clients should use for a started server."""

    host = getattr(server, "axion_host", server.server_address[0])
    return _display_url(host, server.server_address[1])


def run_daemon(
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    allow_network: bool = False,
    output: TextIO | None = None,
) -> None:
    """Run the local daemon until Ctrl-C, then close its socket cleanly."""

    server = start_daemon(host=host, port=port, allow_network=allow_network)
    stream = sys.stdout if output is None else output
    print(f"AXIOM daemon listening at {daemon_url(server)}", file=stream, flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAXIOM daemon stopped.", file=stream)
    finally:
        server.server_close()


def serve_in_thread(
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    allow_network: bool = False,
) -> tuple[ThreadingHTTPServer, Thread]:
    """Start a managed daemon thread for embedding and integration tests."""

    server = start_daemon(host=host, port=port, allow_network=allow_network)
    thread = Thread(target=server.serve_forever, name="axiom-daemon", daemon=True)
    thread.start()
    return server, thread


__all__ = [
    "LOOPBACK_HOSTS",
    "daemon_url",
    "run_daemon",
    "serve_in_thread",
    "start_daemon",
    "validate_bind_host",
]
