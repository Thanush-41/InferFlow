"""
Vercel Python serverless entry point.

Vercel's Python runtime (vc__handler__python.py) requires `handler` to be a
class subclassing BaseHTTPRequestHandler.  We delegate all requests to the
FastAPI ASGI app via a2wsgi's WSGI bridge.

lifespan: startup errors are non-fatal (see main.py resilient lifespan),
so cold-start failures (e.g., Redis timeout) don't block the health endpoint.
"""
import sys
import os
from http.server import BaseHTTPRequestHandler
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from a2wsgi import ASGIMiddleware
from app.main import app as _fastapi_app

_wsgi_app = ASGIMiddleware(_fastapi_app)


class handler(BaseHTTPRequestHandler):
    """Vercel-compatible handler: routes all HTTP methods to FastAPI via WSGI."""

    def do_GET(self):     self._dispatch()
    def do_POST(self):    self._dispatch()
    def do_PUT(self):     self._dispatch()
    def do_DELETE(self):  self._dispatch()
    def do_OPTIONS(self): self._dispatch()
    def do_PATCH(self):   self._dispatch()
    def do_HEAD(self):    self._dispatch()

    def log_message(self, fmt, *args):  # silence BaseHTTPRequestHandler access logs
        pass

    def _dispatch(self):
        import traceback
        print(f"[dispatch] START {self.command} {self.path}", flush=True)
        content_length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(content_length) if content_length else b""

        path, _, query_string = self.path.partition("?")

        environ = {
            "REQUEST_METHOD": self.command,
            "PATH_INFO": path,
            "QUERY_STRING": query_string,
            "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            "CONTENT_LENGTH": str(content_length),
            "SERVER_NAME": "vercel",
            "SERVER_PORT": "443",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "https",
            "wsgi.input": BytesIO(body),
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": True,
        }

        for key, value in self.headers.items():
            key_norm = key.upper().replace("-", "_")
            if key_norm not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                environ[f"HTTP_{key_norm}"] = value

        status_holder = []
        headers_holder = []

        def start_response(status, response_headers, exc_info=None):
            status_holder.append(status)
            headers_holder.extend(response_headers)

        try:
            print(f"[dispatch] calling wsgi_app", flush=True)
            result = _wsgi_app(environ, start_response)

            # a2wsgi returns a lazy generator; start_response is called while
            # iterating — so we must exhaust the body BEFORE reading status_holder.
            print(f"[dispatch] consuming response body", flush=True)
            response_body = b"".join(chunk for chunk in result if chunk)

            status_code = int(status_holder[0].split(" ", 1)[0]) if status_holder else 500
            print(f"[dispatch] status={status_code} body_len={len(response_body)} body={response_body[:200]!r}", flush=True)
            print(f"[dispatch] resp_headers={headers_holder}", flush=True)
            self.send_response(status_code)
            for name, value in headers_holder:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(response_body)
            print(f"[dispatch] DONE", flush=True)
        except Exception as exc:
            print(f"[dispatch] EXCEPTION {type(exc).__name__}: {exc}", flush=True)
            traceback.print_exc()
            import json
            payload = json.dumps({"error": str(exc)}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
