# 3D Viewer

A standalone browser-based viewer for model files. The server scans the selected
model directory recursively and presents supported files in a browser. STEP
assemblies include a part tree with per-part visibility controls.

## Requirements

- Python 3.9 or later; no third-party Python packages are required.
- A modern browser with WebGL and WebAssembly support.
- For STEP/STP, IGES/IGS, and BREP/BRP import, keep the bundled OCCT JavaScript,
  Worker, and WASM files under `static/o3dv/occt/`.

## Start

Install the package, then serve a directory of models:

```sh
python3 -m pip install sin3dviewer
sin3dviewer /path/to/models
```

For development from a source checkout, the compatibility launcher remains
available:

```sh
python3 server.py /path/to/models
```

Options:

```text
--host ADDRESS   Listen address (default: 0.0.0.0)
--port PORT      Listen port (default: 8766)
```

For local-only access, bind to loopback:

```sh
python3 server.py /path/to/models --host 127.0.0.1 --port 8766
```

Open `http://127.0.0.1:8766/` when using loopback. For access from another
device, use the host machine's network address and ensure the chosen port is
reachable. The server does not need to be LAN-exposed when a reverse proxy or
frp tunnel forwards requests to it.

## Features

- Recursively lists supported files from the selected model directory.
- Loads one selected model at a time; STL, STEP/STP, OBJ, 3MF, IGES/IGS, and
  other formats supported by Online3DViewer 0.18.0 are available.
- Shows STEP assembly hierarchy and allows individual nodes/subassemblies to
  be shown or hidden. Single-part models omit the structure panel.
- Includes preset views, fit-to-model, automatic rotation, download, and a
  responsive floating file/structure sidebar.
- Serves O3DV and OCCT dependencies locally from `static/o3dv/`; it does not
  require a CDN for STEP parsing.

## Caching

- Files under `/static/` are cached for one day and revalidated afterward.
- Model files and `/api/models` use ETags with `Cache-Control: no-cache`.
  Unchanged files return `304 Not Modified`; changed files are downloaded
  again. This keeps newly exported CAD models from remaining stale.

## Network and security

The default bind address `0.0.0.0` listens on all interfaces. Anyone who can
reach this server can download every supported model file under the selected
directory. Serve only a directory that is appropriate to expose. For external
access, put the server behind an authenticated HTTPS reverse proxy or an
appropriately restricted tunnel; this application itself does not implement
authentication or access control.

If using frp or another reverse proxy, forward the complete HTTP path space,
including `/api/`, `/models/`, and `/static/`, to the same server. Do not cache
the model catalog or model URLs as immutable content at the proxy; the origin's
ETag validation is needed to detect regenerated models.

## Files

- `src/sin3dviewer/server.py` — standard-library HTTP server and model catalog API.
- `src/sin3dviewer/data/viewer.html` — full-screen browser viewer.
- `src/sin3dviewer/data/static/o3dv/online3dviewer/` — Online3DViewer bundle and license.
- `src/sin3dviewer/data/static/o3dv/occt/` — OCCT importer, Worker, WASM, and license notices.

The Online3DViewer bundle is locally patched so the OCCT Worker and WASM are
loaded from `/static/o3dv/occt/`. When replacing the bundle, preserve this path
configuration and test STEP loading.
