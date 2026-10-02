#!/usr/bin/env python3
"""Prepare a dispatch, or explicitly send it with existing gh authentication.

Acceptance is a transport receipt, not proof of a completed build/deployment.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import subprocess
from uuid import uuid4

from revisions import REPOSITORIES
from triggers import payload, SOURCES


def request(arguments: list[str], body=None) -> str:
    result = subprocess.run(["gh", "api", *arguments], input=json.dumps(body) if body is not None else None,
                            capture_output=True, text=True)
    if result.returncode:
        # gh debug output may contain credentials; never copy it into receipts.
        raise RuntimeError(f"GitHub request failed (exit {result.returncode}); no request acceptance proven")
    return result.stdout


def dispatch(source: str, sha: str | None, identity: str, send: bool) -> dict:
    if source not in SOURCES:
        raise ValueError("Unknown source")
    key, _ = SOURCES[source]
    if send:
        current = json.loads(request([f"repos/{REPOSITORIES[key]}/commits/main"]))["sha"]
        if sha is not None and sha != current:
            raise ValueError("Requested SHA is not the current source main head; refresh it before dispatch")
        sha = current
    if sha is None:
        raise ValueError("Provide --sha for an offline dry run, or use --send to resolve the source main head")
    body = payload(source, sha, identity)
    if send:
        request(["--method", "POST", f"repos/{REPOSITORIES['hub']}/dispatches", "--input", "-"], body)
    return {"receiver": REPOSITORIES["hub"], "accepted": send,
            "mode": "sent" if send else "offline-dry-run", "request": body,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "meaning": "Request acceptance only; verify the matching run and manifest before claiming a build or publication"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=SOURCES, required=True)
    parser.add_argument("--sha", help="Optional current main SHA; required for an offline dry run")
    parser.add_argument("--verification-id", default="verify-" + uuid4().hex)
    parser.add_argument("--send", action="store_true", help="Send the request; default is offline")
    args = parser.parse_args()
    try:
        receipt = dispatch(args.source, args.sha, args.verification_id, args.send)
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(receipt, indent=2))
