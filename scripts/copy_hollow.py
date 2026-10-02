#!/usr/bin/env python3
"""Publish only the game runtime and its vendor license to a new directory."""
import argparse
from pathlib import Path
import shutil

RUNTIME_FILES = (
    "index.html", "styles.css", "app.js", "artwork.js", "harmony-data.js",
    "vendor/opensheetmusicdisplay.min.js",
    "vendor/opensheetmusicdisplay.min.js.LICENSE.txt",
)


def validate_source(source: Path) -> Path:
    source = source.resolve(strict=True)
    for relative in RUNTIME_FILES:
        path = source / relative
        if any(part.is_symlink() for part in (path, *path.parents) if part != source and source in part.parents):
            raise ValueError(f"Runtime asset may not be a symlink: {relative}")
        if not path.is_file():
            raise ValueError(f"Required runtime file missing: {relative}")
    return source


def copy_runtime(source: Path, destination: Path) -> None:
    source = validate_source(source)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Refusing existing publication directory: {destination}")
    if destination.resolve().is_relative_to(source):
        raise ValueError("Publication must be outside the source checkout")
    destination.mkdir(parents=True, exist_ok=False)
    for relative in RUNTIME_FILES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    copy_runtime(args.source, args.destination)
    print(f"Published {len(RUNTIME_FILES)} runtime/license files to {args.destination}")
