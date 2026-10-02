"""Record exact checkout identities without publishing credential-bearing remotes."""
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import re
import subprocess

REPOSITORIES = {
    "hub": "jjjhenriksen/shapenote-site",
    "atlas": "jjjhenriksen/shapenote-atlas",
    "local_ai": "jjjhenriksen/sacred-harp-finetune",
    "hollow_square": "jjjhenriksen/hollow-square",
}


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE).strip()


def revision(root: Path, key: str, allow_dirty: bool = False, exclude_roots=()) -> dict:
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root.resolve():
        raise ValueError(f"{key} must be the checkout root")
    commit = git(root, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError(f"{key} does not have a full commit SHA")
    pathspecs = ["."]
    for excluded in exclude_roots:
        if excluded.resolve().is_relative_to(root.resolve()):
            pathspecs.append(f":(exclude){excluded.resolve().relative_to(root.resolve()).as_posix()}")
    dirty = bool(git(root, "status", "--porcelain", "--untracked-files=all", "--", *pathspecs))
    if dirty and not allow_dirty:
        raise ValueError(f"{key} has uncommitted changes; preserve them or use --allow-dirty for a labeled preview")
    repository = REPOSITORIES[key]
    origin = git(root, "remote", "get-url", "origin")
    allowed = {f"https://github.com/{repository}", f"https://github.com/{repository}.git",
               f"git@github.com:{repository}.git", f"ssh://git@github.com/{repository}.git"}
    if origin not in allowed:
        raise ValueError(f"{key} origin does not match the documented repository; remote value withheld")
    return {"repository": repository, "commit": commit, "dirty": dirty}


def version(command: str):
    try:
        return subprocess.check_output([command, "--version"], text=True, stderr=subprocess.PIPE, timeout=10).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def manifest(roots: dict[str, Path], atlas_built: bool, allow_dirty: bool) -> dict:
    if os.environ.get("ATLAS_PUBLIC_DIR"):
        raise ValueError("Unset ATLAS_PUBLIC_DIR for publication; the canonical source tree must be used")
    # Actions checks the three independent repos out beneath the hub. They are
    # audited separately and are not uncommitted additions to the hub history.
    independent = [root for key, root in roots.items() if key != "hub"]
    revisions = {key: revision(root, key, allow_dirty, independent if key == "hub" else ())
                 for key, root in roots.items()}
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": revisions,
        "build": {
            "atlas_base": "/atlas/",
            "atlas_mode": "prebuilt-unverified" if atlas_built else "npm-ci-vite-build",
            "clean_source_revisions": all(not source["dirty"] for source in revisions.values()),
            "node": version("node"), "npm": version("npm"), "python": platform.python_version(),
        },
        "limitations": "SHAs identify clean source revisions, not uncommitted/ignored extras or an unverified prebuilt dist. Environment/byte identity requires separate comparison.",
    }
