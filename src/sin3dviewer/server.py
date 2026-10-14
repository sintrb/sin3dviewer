"""Serve a local directory of 3D models to the browser viewer."""

import argparse
import hashlib
import json
import mimetypes
from email.utils import formatdate, parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


DATA_DIR = Path(__file__).resolve().parent / "data"
VIEWER_FILE = DATA_DIR / "viewer.html"
STATIC_DIR = DATA_DIR / "static"
SUPPORTED_EXTENSIONS = {
    ".3dm", ".3ds", ".3mf", ".amf", ".brep", ".brp", ".dae", ".fbx",
    ".fcstd", ".glb", ".gltf", ".ifc", ".iges", ".igs", ".off", ".obj",
    ".ply", ".step", ".stl", ".stp", ".wrl",
}
mimetypes.add_type("model/step", ".step")
mimetypes.add_type("model/step", ".stp")
mimetypes.add_type("application/wasm", ".wasm")


def model_catalog(model_dir):
    models = []
    for path in model_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            relative = path.relative_to(model_dir).as_posix()
            models.append(
                {
                    "name": path.name,
                    "path": relative,
                    "format": path.suffix[1:].upper(),
                    "bytes": path.stat().st_size,
                }
            )
        except (OSError, ValueError):
            continue
    return sorted(models, key=lambda item: (item["path"].lower(), item["format"]))


def contained_file(base, relative_path):
    candidate = (base / relative_path).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


class ViewerHandler(BaseHTTPRequestHandler):
    server_version = "LocalModelViewer/2.0"

    def _send(self, status, content_type, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        etag = f'"{hashlib.sha256(data).hexdigest()}"'
        if self._is_not_modified(etag, None):
            self._send_not_modified(etag, None, "no-cache")
            return
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("ETag", etag)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _is_not_modified(self, etag, last_modified):
        request_etags = self.headers.get("If-None-Match")
        if request_etags is not None:
            normalized_etag = etag.removeprefix("W/")
            return any(
                candidate.strip() == "*"
                or candidate.strip().removeprefix("W/") == normalized_etag
                for candidate in request_etags.split(",")
            )
        modified_since = self.headers.get("If-Modified-Since")
        if modified_since is None or last_modified is None:
            return False
        try:
            since_timestamp = parsedate_to_datetime(modified_since).timestamp()
            modified_timestamp = parsedate_to_datetime(last_modified).timestamp()
            return modified_timestamp <= since_timestamp
        except (TypeError, ValueError, OverflowError):
            return False

    def _send_not_modified(self, etag, last_modified, cache_control):
        self.send_response(304)
        self.send_header("Cache-Control", cache_control)
        self.send_header("ETag", etag)
        if last_modified is not None:
            self.send_header("Last-Modified", last_modified)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

    def _send_file(self, path, cache_control):
        stat = path.stat()
        etag = f'W/"{stat.st_size:x}-{stat.st_mtime_ns:x}"'
        last_modified = formatdate(stat.st_mtime, usegmt=True)
        if self._is_not_modified(etag, last_modified):
            self._send_not_modified(etag, last_modified, cache_control)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(stat.st_size))
        self.send_header("Content-Disposition", f'inline; filename="{path.name}"')
        self.send_header("Cache-Control", cache_control)
        self.send_header("ETag", etag)
        self.send_header("Last-Modified", last_modified)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            with path.open("rb") as file:
                while chunk := file.read(1024 * 1024):
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            return self._send(200, "text/html; charset=utf-8", VIEWER_FILE.read_bytes())
        if path == "/api/models":
            return self._send(
                200,
                "application/json; charset=utf-8",
                json.dumps(model_catalog(self.server.model_dir)),
            )
        if path.startswith("/models/"):
            relative = path.removeprefix("/models/")
            model = contained_file(self.server.model_dir, relative)
            if model is None or model.suffix.lower() not in SUPPORTED_EXTENSIONS:
                return self._send(404, "text/plain; charset=utf-8", "model not found")
            return self._send_file(model, "no-cache")
        if path.startswith("/static/"):
            static_file = contained_file(STATIC_DIR, path.removeprefix("/static/"))
            if static_file is None:
                return self._send(404, "text/plain; charset=utf-8", "asset not found")
            return self._send_file(
                static_file,
                "public, max-age=86400, must-revalidate",
            )
        self._send(404, "text/plain; charset=utf-8", "not found")

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="directory to browse (default: current working directory)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="listen interface (default: all network interfaces)",
    )
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args(argv)
    model_dir = Path(args.directory).expanduser().resolve()
    if not model_dir.is_dir():
        raise SystemExit(f"Model directory does not exist: {model_dir}")
    models = model_catalog(model_dir)

    server = ThreadingHTTPServer((args.host, args.port), ViewerHandler)
    server.model_dir = model_dir
    print(f"Model directory: {model_dir}")
    print(f"Viewer URL: http://{args.host}:{server.server_port}/")
    print(f"Model count: {len(models)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down model viewer")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
