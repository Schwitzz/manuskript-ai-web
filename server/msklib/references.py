"""Cross references like {C:3:Name}, {T:12:Title}, {P:2:Plot}, {W:5:Place}.

Same pattern and letters as desktop Manuskript (manuskript/models/references.py). They live
as plain text in scenes, notes and summaries, so they round-trip with no special handling;
this module only finds and resolves them.
"""

from __future__ import annotations

import re

from msklib.project import Project

PATTERN = re.compile(r"{(\w):(\d+):?.*?}")
KINDS = {"C": "character", "T": "scene", "P": "plot", "W": "world"}
LETTER = {v: k for k, v in KINDS.items()}


def make(kind: str, item_id: int, title: str = "") -> str:
    return "{%s:%d:%s}" % (LETTER[kind], item_id, title)


def find(text: str) -> list[tuple[str, int]]:
    """Every (kind, id) referenced in `text`, in order, with unknown letters skipped."""
    return [(KINDS[m.group(1)], int(m.group(2))) for m in PATTERN.finditer(text or "")
            if m.group(1) in KINDS]


def _world_names(items) -> dict[int, str]:
    out: dict[int, str] = {}
    for root in items:
        out[root.id] = root.name
        for it in root.walk():
            out[it.id] = it.name
    return out


def title_of(project: Project, kind: str, item_id: int) -> str | None:
    """Current title of the referenced thing, or None if it no longer exists."""
    if kind == "scene":
        item = project.find(item_id)
        return item.title if item else None
    if kind == "character":
        return next((c.name for c in project.characters if c.id == item_id), None)
    if kind == "plot":
        return next((p.name for p in project.plots if p.id == item_id), None)
    if kind == "world":
        return _world_names(project.world).get(item_id)
    return None


def _sources(project: Project):
    """(source kind, id, title, field, text) for every place a reference can be written."""
    for item in project.outline.walk():
        for field, text in (("text", "" if item.is_folder else item.text),
                            ("notes", item.meta.get("notes", "")),
                            ("summary", item.meta.get("summaryFull", "")
                             + "\n" + item.meta.get("summarySentence", ""))):
            yield "scene", item.id, item.title, field, text
    for c in project.characters:
        for field, text in (("notes", c.notes), ("summary", c.summary_full + "\n" + c.summary_para)):
            yield "character", c.id, c.name, field, text
    for pl in project.plots:
        yield "plot", pl.id, pl.name, "description", pl.attrs.get("description", "")
    for root in project.world:
        for w in [root, *root.walk()]:
            yield "world", w.id, w.name, "description", w.attrs.get("description", "")


def backlinks(project: Project, kind: str, item_id: int) -> list[dict]:
    """Everything that mentions (kind, item_id)."""
    out = []
    for skind, sid, title, field, text in _sources(project):
        n = sum(1 for k, i in find(text) if (k, i) == (kind, item_id))
        if n and (skind, sid) != (kind, item_id):
            out.append({"kind": skind, "id": sid, "title": title, "field": field, "count": n})
    return out


def broken(project: Project) -> list[dict]:
    """References whose target no longer exists."""
    out = []
    for skind, sid, title, field, text in _sources(project):
        for k, i in find(text):
            if title_of(project, k, i) is None:
                out.append({"source_kind": skind, "source_id": sid, "source_title": title,
                            "field": field, "target_kind": k, "target_id": i})
    return out
