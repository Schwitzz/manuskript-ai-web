"""Change notifications: an in-process bus plus a disk watcher for edits made elsewhere.

Each project has a signature (file names, sizes, mtimes). Any request that changes it, and
any change noticed by the watcher (desktop app, sync pass), publishes one "changed" event.
The watcher only runs while at least one browser is subscribed.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from app.config import get_settings

_subscribers: set[asyncio.Queue] = set()
_known: dict[str, str] = {}
WATCH_INTERVAL = 2.0


def signature(root: Path) -> str:
    parts = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for f in sorted(files):
            if f.startswith("."):
                continue
            try:
                st = os.stat(os.path.join(dirpath, f))
            except OSError:
                continue
            parts.append(f"{os.path.relpath(os.path.join(dirpath, f), root)}:{st.st_size}:{st.st_mtime_ns}")
    return str(hash("|".join(parts)))


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)


def has_subscribers() -> bool:
    return bool(_subscribers)


def publish(event: dict) -> None:
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass  # a stuck browser must never block the server; it resyncs on reconnect


def note_signature(name: str, root: Path) -> bool:
    """Record the project's current signature; True if it differs from the last known one."""
    sig = signature(root)
    changed = _known.get(name) not in (None, sig)
    _known[name] = sig
    return changed


def forget(name: str) -> None:
    _known.pop(name, None)


def check_all() -> list[str]:
    """Names of projects that changed on disk since last looked at."""
    root = get_settings().projects_dir
    if not root.is_dir():
        return []
    changed = []
    for d in root.iterdir():
        if d.is_dir() and not d.name.startswith(".") and (d / "MANUSKRIPT").exists():
            if note_signature(d.name, d):
                changed.append(d.name)
    return changed


async def watcher() -> None:
    """Background task: poll the disk while someone is listening."""
    while True:
        await asyncio.sleep(WATCH_INTERVAL)
        if not has_subscribers():
            _known.clear()  # start fresh next time so we never report old changes
            continue
        for name in await asyncio.to_thread(check_all):
            publish({"type": "changed", "project": name, "source": "external"})
