import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SERVICE_NAME = "file-manager"
VERSION = "1.2.0"


class HealthHandler(BaseHTTPRequestHandler):
    """Служебный HTTP-интерфейс: только статус, без доступа к файлам и базе."""

    def do_GET(self):
        if self.path == "/healthz":
            self._respond(200, {
                "status": "ok",
                "service": SERVICE_NAME,
                "version": VERSION,
                "secret_configured": bool(os.environ.get("APP_SECRET")),
            })
        elif self.path == "/":
            self._respond(200, {
                "service": SERVICE_NAME,
                "version": VERSION,
                "endpoints": ["/healthz"],
            })
        else:
            self._respond(404, {"status": "not_found"})

    def _respond(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), HealthHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()