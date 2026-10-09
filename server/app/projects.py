"""Project store: finds projects on disk, serialises access, and guards names.

Files are the source of truth. Every request loads the project fresh from disk under a
per-project lock, so edits made elsewhere (desktop app, sync) are never hidden by a cache.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import threading
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException

from app import events, synclock
from app.config import get_settings
from msklib.model import Item
from msklib.project import Project

_NAME_OK = re.compile(r"^[^/\\\x00]{1,100}$")
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def valid_name(name: str) -> str:
    if not _NAME_OK.match(name) or name.startswith(".") or name in (".", ".."):
        raise HTTPException(400, "Invalid project name")
    return name


def project_path(name: str) -> Path:
    valid_name(name)
    root = get_settings().projects_dir
    path = (root / name).resolve()
    if root.resolve() not in path.parents:
        raise HTTPException(400, "Invalid project name")
    return path


def list_projects() -> list[dict]:
    root = get_settings().projects_dir
    if not root.is_dir():
        return []
    out = []
    for d in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if d.is_dir() and not d.name.startswith(".") and (d / "MANUSKRIPT").exists():
            title = d.name
            try:
                title = Project.load(d).infos.get("Title") or d.name
            except Exception:  # a broken project must not hide the others
                pass
            out.append({"name": d.name, "title": title})
    return out


def _guard_writes(project: Project, path: Path) -> None:
    """While a sync pass holds the .lock marker, reads work but any save is refused (423).
    Done on the Project itself so no endpoint can forget to check."""
    real_save = project.save

    def guarded_save():
        if synclock.is_locked(path):
            raise HTTPException(423, "A sync is running for this project. Try again in a moment.")
        return real_save()

    project.save = guarded_save  # type: ignore[method-assign]


def _lock_for(name: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(name, threading.Lock())


@contextmanager
def open_project(name: str):
    """Yield a freshly loaded Project while holding that project's lock."""
    path = project_path(name)
    if not (path / "MANUSKRIPT").exists():
        raise HTTPException(404, "Project not found")
    with _lock_for(name):
        before = events.signature(path) if events.has_subscribers() else None
        project = Project.load(path)
        _guard_writes(project, path)
        yield project
        if before is not None and events.signature(path) != before:
            events.note_signature(name, path)
            events.publish({"type": "changed", "project": name, "source": "api"})


def create_project(name: str, title: str, author: str = "") -> None:
    path = project_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock_for(name):
        try:
            Project.create(path, title, author)
        except FileExistsError:
            raise HTTPException(409, "A project with that name already exists")


SAMPLES_DIR = Path(__file__).parent / "samples"


def list_samples() -> list[str]:
    if not SAMPLES_DIR.is_dir():
        return []
    return sorted(d.name for d in SAMPLES_DIR.iterdir() if (d / "MANUSKRIPT").exists())


def create_from_sample(name: str, sample: str) -> None:
    """Copy a bundled sample project to a new project called `name`."""
    if sample not in list_samples():
        raise HTTPException(404, "Unknown sample")
    path = project_path(name)
    marker = path.with_name(path.name + ".msk")
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock_for(name):
        if path.exists() or marker.exists():
            raise HTTPException(409, "A project with that name already exists")
        shutil.copytree(SAMPLES_DIR / sample, path, ignore=shutil.ignore_patterns(".*"))
        marker.write_text("1", encoding="utf8")


def doc_version(item: Item) -> str:
    """Content hash: changes whenever the text changes, wherever the change came from."""
    return hashlib.sha256(item.text.encode("utf8")).hexdigest()[:16]


def item_summary(item: Item) -> dict:
    return {
        "id": item.id, "title": item.title, "type": item.type,
        "meta": dict(item.meta),
        "children": [item_summary(c) for c in item.children],
    }
