from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import json

from forge_manager.config import Config
from forge_manager.db import Store
from forge_manager.reports import project_report, status_report, structure_report
from forge_manager.reports.status import day_bounds, range_bounds


STATIC_DIR = Path(__file__).parent / "static"


def serve_dashboard(config: Config, store: Store, host: str, port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                return self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            if parsed.path == "/app.js":
                return self._send_file(STATIC_DIR / "app.js", "text/javascript; charset=utf-8")
            if parsed.path == "/style.css":
                return self._send_file(STATIC_DIR / "style.css", "text/css; charset=utf-8")
            if parsed.path == "/api/structure":
                qs = parse_qs(parsed.query)
                view = qs.get("view", ["tree"])[0]
                active = qs.get("active", ["0"])[0] in {"1", "true", "yes"}
                return self._send_json({"text": structure_report(store, view, active)})
            if parsed.path == "/api/status":
                qs = parse_qs(parsed.query)
                view = qs.get("view", ["list"])[0]
                if "from" in qs and "to" in qs:
                    start, end = range_bounds(qs["from"][0], qs["to"][0])
                else:
                    start, end = day_bounds()
                return self._send_json({"text": status_report(store, start, end, view)})
            if parsed.path == "/api/project":
                qs = parse_qs(parsed.query)
                project_id = qs.get("id", ["forge"])[0]
                view = qs.get("view", ["list"])[0]
                return self._send_json({"text": project_report(store, project_id, view)})
            self.send_error(404)

        def _send_file(self, path: Path, content_type: str) -> None:
            if not path.exists():
                self.send_error(404)
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, data: dict) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"forge-manager dashboard: http://{host}:{port}")
    server.serve_forever()
