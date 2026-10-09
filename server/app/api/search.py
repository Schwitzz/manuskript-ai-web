"""Full-text search across scenes, summaries, notes and characters.

Scans the project files on every request instead of keeping an index, so results can never
be stale after an edit made by the desktop app or a sync pass. Fine for one user's project.
"""

import re

from fastapi import APIRouter, Depends, Query

from app import projects as store
from app.auth.deps import current_user

router = APIRouter(prefix="/api/projects/{name}/search", tags=["search"],
                   dependencies=[Depends(current_user)])

SCOPES = {"text", "summary", "notes", "characters"}
MAX_RESULTS = 200
CONTEXT = 60


def _snippets(text: str, pattern: re.Pattern, limit: int = 3) -> list[str]:
    out = []
    for m in pattern.finditer(text):
        a, b = max(0, m.start() - CONTEXT), min(len(text), m.end() + CONTEXT)
        out.append(("…" if a else "") + text[a:b].replace("\n", " ") + ("…" if b < len(text) else ""))
        if len(out) >= limit:
            break
    return out


@router.get("")
def search(name: str, q: str = Query(min_length=1, max_length=200),
           scope: str = "text,summary,notes,characters", case: bool = False, word: bool = False):
    scopes = {s for s in scope.split(",") if s in SCOPES} or SCOPES
    expr = re.escape(q)
    if word:
        expr = rf"\b{expr}\b"
    pattern = re.compile(expr, 0 if case else re.IGNORECASE)
    results = []
    with store.open_project(name) as p:
        for item in p.outline.walk():
            fields = {"text": "" if item.is_folder else item.text,
                      "summary": "\n".join(item.meta.get(k, "") for k in
                                           ("summarySentence", "summaryFull")),
                      "notes": item.meta.get("notes", "")}
            for kind in ("text", "summary", "notes"):
                if kind in scopes and pattern.search(fields[kind]):
                    results.append({"kind": kind, "id": item.id, "title": item.title,
                                    "matches": len(pattern.findall(fields[kind])),
                                    "snippets": _snippets(fields[kind], pattern)})
        if "characters" in scopes:
            for c in p.characters:
                blob = "\n".join([c.name, c.motivation, c.goal, c.conflict, c.epiphany,
                                  c.summary_sentence, c.summary_para, c.summary_full, c.notes,
                                  *[f"{k}: {v}" for k, v in c.infos]])
                if pattern.search(blob):
                    results.append({"kind": "character", "id": c.id, "title": c.name,
                                    "matches": len(pattern.findall(blob)),
                                    "snippets": _snippets(blob, pattern)})
    return {"query": q, "truncated": len(results) > MAX_RESULTS, "results": results[:MAX_RESULTS]}
