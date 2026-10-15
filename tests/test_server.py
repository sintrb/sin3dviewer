import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from sin3dviewer.server import ThreadingHTTPServer, ViewerHandler, model_catalog


class ModelCatalogTests(unittest.TestCase):
    def test_catalog_is_recursive_and_ignores_unsupported_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "nested").mkdir()
            (root / "nested" / "part.STEP").write_bytes(b"step")
            (root / "notes.txt").write_text("ignore")

            self.assertEqual(
                model_catalog(root),
                [{"name": "part.STEP", "path": "nested/part.STEP", "format": "STEP", "bytes": 4, "modified": (root / "nested" / "part.STEP").stat().st_mtime}],
            )


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.model_dir = Path(self.tempdir.name)
        (self.model_dir / "cube.stl").write_bytes(b"solid cube")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ViewerHandler)
        self.server.model_dir = self.model_dir
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tempdir.cleanup()

    def test_catalog_and_packaged_viewer_are_served(self):
        connection = HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request("GET", "/api/models")
        response = connection.getresponse()
        catalog = json.loads(response.read())
        self.assertEqual(response.status, 200)
        self.assertEqual(catalog[0]["path"], "cube.stl")

        connection.request("GET", "/")
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn("3D Model Viewer", response.read().decode("utf-8"))

        connection.request("GET", "/static/o3dv/online3dviewer/o3dv.min.js")
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertGreater(int(response.getheader("Content-Length")), 0)
        response.read()
        connection.close()


if __name__ == "__main__":
    unittest.main()
