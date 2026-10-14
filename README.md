# sin3dviewer

A small, dependency-free Python HTTP server for previewing 3D model files in a
browser. It recursively indexes a directory and serves the bundled viewer and
its JavaScript/WebAssembly dependencies locally.

## Install and run

Python 3.9 or later is required. Install from PyPI:

```sh
python -m pip install sin3dviewer
sin3dviewer /path/to/models --port 8767
```

Then open `http://127.0.0.1:8767/`. The default bind address is `0.0.0.0`, so
other machines that can reach the host may access and download files from the
selected directory. Use `--host 127.0.0.1` for local-only access.

Options:

```text
sin3dviewer [directory] [--host ADDRESS] [--port PORT]
```

The directory defaults to the current working directory and the port defaults
to `8766`. The same command is available as `python -m sin3dviewer`.

## Development

```sh
python -m pip install -e ".[dev]"
sin3dviewer /path/to/models
python -m unittest discover -s tests
python -m build
```

The source-checkout launcher `python server.py [directory]` remains supported.
The server uses only the Python standard library at runtime. The packaged
Online3DViewer and OCCT assets retain their upstream license notices under
`src/sin3dviewer/data/static/o3dv/`.

To publish a release, update `__version__` in `src/sin3dviewer/__init__.py`,
build and inspect the artifacts, then upload the
contents of `dist/` with a PyPI publishing tool such as `twine`.

## Security

Anyone who can reach the server can list and download supported model files
under the selected directory. Do not expose sensitive directories to an
untrusted network. For remote access, use an authenticated HTTPS reverse proxy
or a restricted tunnel; the application itself does not provide
authentication.
