"""Bounded source-to-hub dispatch contract; payload metadata is never code."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re

from revisions import REPOSITORIES

SOURCES = {
    "atlas": ("atlas", "atlas-updated"),
    "local-ai": ("local_ai", "local-ai-updated"),
    "hollow-square": ("hollow_square", "hollow-square-updated"),
}


def payload(source: str, sha: str, verification_id: str) -> dict:
    if source not in SOURCES:
        raise ValueError("Unknown source")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Source revision must be a full lowercase commit SHA")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", verification_id):
        raise ValueError("Verification ID must be 1–80 ASCII letters, digits, hyphens or underscores")
    key, event_type = SOURCES[source]
    return {"event_type": event_type, "client_payload": {
        "repository": REPOSITORIES[key], "sha": sha, "verification_id": verification_id,
    }}


def trigger_info(event_name: str, event: dict | None = None) -> dict:
    result = {"event": event_name}
    if event_name != "repository_dispatch":
        return result
    event = event or {}
    action = event.get("action")
    source = next((name for name, (_, event_type) in SOURCES.items() if event_type == action), None)
    if source is None:
        raise ValueError("Unknown dispatch type")
    body = event.get("client_payload", {})
    if not isinstance(body, dict):
        raise ValueError("Dispatch metadata must be an object")
    key, _ = SOURCES[source]
    repository, sha, identity = (body.get(name) for name in ("repository", "sha", "verification_id"))
    if repository is not None and repository != REPOSITORIES[key]:
        raise ValueError("Dispatch type/source mismatch; supplied value withheld")
    if sha is not None and (not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha)):
        raise ValueError("Dispatch SHA must be a full lowercase commit SHA")
    if identity is not None and (not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identity)):
        raise ValueError("Invalid verification ID; supplied value withheld")
    result.update(type=action, source_key=key, requested_repository=repository,
                  requested_commit=sha, verification_id=identity)
    return result


def current_trigger() -> dict:
    name = os.environ.get("GITHUB_EVENT_NAME", "local")
    event = None
    if name == "repository_dispatch":
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    return trigger_info(name, event)
