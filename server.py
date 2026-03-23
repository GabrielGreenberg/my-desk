#!/usr/bin/env python3
"""Tiny dev server that serves static files and persists items to data.json."""

import json, os, http.server

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, "data.json")
ARCHIVE_FILE = os.path.join(BASE, "archive.json")

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/items":
            self._send_json(self._read(DATA_FILE, []))
        elif self.path == "/api/archive":
            self._send_json(self._read(ARCHIVE_FILE, []))
        else:
            super().do_GET()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        data = json.loads(body)
        if self.path == "/api/items":
            self._write(DATA_FILE, data)
            self._send_json({"ok": True})
        elif self.path == "/api/archive":
            archive = self._read(ARCHIVE_FILE, [])
            if isinstance(data, list):
                archive.extend(data)
            else:
                archive.append(data)
            self._write(ARCHIVE_FILE, archive)
            self._send_json({"ok": True})
        else:
            self.send_error(404)

    def _read(self, path, default):
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return default

    def _write(self, path, obj):
        with open(path, "w") as f:
            json.dump(obj, f, indent=2)

    def _send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    os.chdir(BASE)
    port = int(os.environ.get("PORT", 8000))
    server = http.server.HTTPServer(("", port), Handler)
    print(f"Serving on http://localhost:{port}")
    server.serve_forever()
