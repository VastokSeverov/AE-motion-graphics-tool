#!/usr/bin/env python3
"""Local-only bridge for the VASTOCHNIY still-image background remover."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path
import json
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
from background_remover import remove_background, BackgroundRemovalError

HOST, PORT = "127.0.0.1", 8766
MAX_REQUEST_BYTES = 16384

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[bridge] " + (fmt % args), flush=True)

    def send_json(self, data, code=200):
        raw = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8766")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8766")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if urlparse(self.path).path == "/api/status":
            self.send_json({"ok": True, "bridgeReady": True, "feature": "background-removal"})
        else:
            self.send_json({"error": "Not found. Open the VASTOCHNIY panel inside After Effects."}, 404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/remove-background":
            self.send_json({"error": "Not found. Only background removal is enabled."}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                self.send_json({"error": "Invalid request size."}, 400)
                return
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("JSON object required")
        except Exception:
            self.send_json({"error": "Invalid JSON request."}, 400)
            return
        source = data.get("source_path")
        if not isinstance(source, str) or not source.strip():
            self.send_json({"error": "Select a still image layer in After Effects first."}, 400)
            return
        print("[background-remover] Processing: " + source, flush=True)
        try:
            output = remove_background(source)
            print("[background-remover] Saved: " + str(output), flush=True)
            self.send_json({"ok": True, "output_path": str(output), "message": "Background removed locally."})
        except BackgroundRemovalError as exc:
            print("[background-remover] " + str(exc), flush=True)
            self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            traceback.print_exc()
            self.send_json({"error": "Unexpected background-removal error: " + str(exc)}, 500)

def main():
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        print("Could not start bridge on " + HOST + ":" + str(PORT) + ". Stop any old bridge process first. " + str(exc), file=sys.stderr)
        raise
    print("VASTOCHNIY Background Remover running at http://" + HOST + ":" + str(PORT), flush=True)
    print("Inference runs locally. Keep this Terminal window open; Ctrl+C stops the bridge.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping bridge…", flush=True)
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
