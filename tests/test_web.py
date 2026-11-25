import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from file_manager.web import HealthHandler


def _serve():
    server = ThreadingHTTPServer(("127.0.0.1", 0), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _get(port, path):
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, json.loads(response.read().decode("utf-8"))
    finally:
        connection.close()


def test_healthz_ok():
    server = _serve()
    try:
        status, body = _get(server.server_address[1], "/healthz")
        assert status == 200
        assert body["status"] == "ok"
        assert body["service"] == "file-manager"
        assert body["secret_configured"] in (True, False)
    finally:
        server.shutdown()
        server.server_close()


def test_secret_value_never_leaks(monkeypatch):
    monkeypatch.setenv("APP_SECRET", "super-secret-value-123456")
    server = _serve()
    try:
        status, body = _get(server.server_address[1], "/healthz")
        assert status == 200
        assert body["secret_configured"] is True
        assert "super-secret-value-123456" not in json.dumps(body)
    finally:
        server.shutdown()
        server.server_close()


def test_unknown_path_is_404():
    server = _serve()
    try:
        status, body = _get(server.server_address[1], "/nope")
        assert status == 404
        assert body["status"] == "not_found"
    finally:
        server.shutdown()
        server.server_close()