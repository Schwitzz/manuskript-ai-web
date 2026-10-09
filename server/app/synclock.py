"""`.lock` marker: present in a project folder while a sync pass is running.

While it exists the web app refuses to WRITE (reads still work), so a sync pass never sees
a half-changed project. The marker records who made it and when; one older than MAX_AGE is
treated as left behind by a crashed pass and ignored, so a project can never stay locked.
The name starts with a dot, so desktop Manuskript and msklib ignore it, and sync excludes it.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

LOCK_NAME = ".lock"
MAX_AGE = 15 * 60  # seconds; a sync pass that takes longer must refresh the marker


def lock_path(project: Path) -> Path:
    return project / LOCK_NAME


def read(project: Path) -> dict | None:
    """The active marker, or None if absent, unreadable or expired."""
    try:
        data = json.loads(lock_path(project).read_text(encoding="utf8"))
        if time.time() - float(data["at"]) > MAX_AGE:
            return None
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return None


def is_locked(project: Path) -> bool:
    return read(project) is not None


def acquire(project: Path, owner: str = "sync") -> bool:
    """Create the marker atomically. False if a live marker already exists."""
    if is_locked(project):
        return False
    path = lock_path(project)
    payload = json.dumps({"owner": owner, "pid": os.getpid(), "at": time.time()})
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(payload, encoding="utf8")
    try:
        if path.exists():  # an expired marker: replace it
            os.replace(tmp, path)
        else:
            os.link(tmp, path)  # fails if another process created it first
            tmp.unlink()
    except FileExistsError:
        tmp.unlink(missing_ok=True)
        return False
    return True


def refresh(project: Path) -> None:
    data = read(project)
    if data is not None:
        data["at"] = time.time()
        lock_path(project).write_text(json.dumps(data), encoding="utf8")


def release(project: Path) -> None:
    lock_path(project).unlink(missing_ok=True)


@contextmanager
def held(project: Path, owner: str = "sync"):
    if not acquire(project, owner):
        raise RuntimeError("project is locked")
    try:
        yield
    finally:
        release(project)
