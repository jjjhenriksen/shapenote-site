#!/usr/bin/env python3
"""Build the independent Atlas and assemble a new publication directory."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import tempfile

from copy_hollow import copy_runtime, validate_source

HUB_FILES = ("index.html", "styles.css", "CNAME", ".nojekyll")


def require_files(root: Path, names) -> None:
    for name in names:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Required regular file missing or symlinked: {path}")


def copy_tree(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_dir():
        raise ValueError(f"Required regular directory missing or symlinked: {source}")
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Publication tree contains a symlink: {path}")
    shutil.copytree(source, destination)


def assemble(hub: Path, atlas: Path, local_ai: Path, hollow: Path,
             output: Path, atlas_built: bool = False) -> Path:
    hub, atlas, local_ai = (path.resolve(strict=True) for path in (hub, atlas, local_ai))
    hollow = validate_source(hollow)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing existing output: {output}; preserve/move it before rebuilding")
    if any(output.resolve().is_relative_to(source) for source in (atlas, local_ai, hollow)):
        raise ValueError("Output must be outside the three source checkouts")
    require_files(hub, HUB_FILES)
    require_files(atlas, ("package.json", "package-lock.json"))
    require_files(local_ai, ("presentation/index.html",))
    if not atlas_built:
        subprocess.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=atlas, check=True)
        subprocess.run(["npm", "run", "build", "--", "--base=/atlas/"], cwd=atlas, check=True)
    require_files(atlas, ("dist/index.html",))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as temporary:
        staged = Path(temporary) / "publication"
        staged.mkdir()
        copy_tree(atlas / "dist", staged / "atlas")
        copy_tree(local_ai / "presentation", staged / "local-ai")
        copy_runtime(hollow, staged / "hollow-square")
        for name in HUB_FILES:
            shutil.copy2(hub / name, staged / name)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Output appeared during assembly: {output}")
        staged.rename(output)
    return output


def serve(output: Path, port: int) -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(output))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"Preview http://127.0.0.1:{server.server_port}/ (Ctrl-C to stop)", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hub", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--atlas", type=Path, required=True)
    parser.add_argument("--local-ai", type=Path, required=True)
    parser.add_argument("--hollow-square", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--atlas-built", action="store_true", help="Use an existing dist built with base=/atlas/")
    parser.add_argument("--serve", type=int, metavar="PORT", help="Serve the completed output on loopback")
    args = parser.parse_args()
    output = assemble(args.hub, args.atlas, args.local_ai, args.hollow_square, args.output, args.atlas_built)
    print(f"Assembled publication: {output}", flush=True)
    if args.serve is not None:
        serve(output, args.serve)
