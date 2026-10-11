"""Build the project context that goes to the model with each chat message.

Pure function of a loaded msklib Project, so it can be tested without a server or a model.
Each source is a (key, heading, text) part; `fit` then trims the parts to a token budget.
"""

from __future__ import annotations

from app.ai import estimateTokens
from msklib.project import Project

ORDER = ("selection", "scene", "summary", "pov", "book")
CHAR_FIELDS = (("motivation", "Motivation"), ("goal", "Goal"), ("conflict", "Conflict"),
               ("summary_full", "Summary"), ("notes", "Notes"))


def parts(project: Project, sources: dict[str, bool], scene_id: int | None) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    scene = project.find(scene_id) if scene_id is not None else None
    if scene is not None and scene.is_folder:
        scene = None

    if sources.get("scene") and scene is not None and scene.text.strip():
        out.append(("scene", f"Current scene: {scene.title}", scene.text))

    if sources.get("summary") and scene is not None:
        bits = []
        if scene.meta.get("summarySentence"):
            bits.append(f"Summary: {scene.meta['summarySentence']}")
        if scene.meta.get("summaryFull"):
            bits.append(f"Full summary: {scene.meta['summaryFull']}")
        if scene.meta.get("notes"):
            bits.append(f"Notes: {scene.meta['notes']}")
        if bits:
            out.append(("summary", "Scene summary", "\n".join(bits)))

    if sources.get("pov") and scene is not None:
        pov = scene.meta.get("POV", "")
        char = next((c for c in project.characters if str(c.id) == pov), None) if pov.isdigit() else None
        if char is not None:
            bits = [f"Name: {char.name}"]
            bits += [f"{label}: {getattr(char, attr)}" for attr, label in CHAR_FIELDS if getattr(char, attr, "")]
            out.append(("pov", "POV character", "\n".join(bits)))

    if sources.get("book"):
        info = project.infos
        bits = [f"{label}: {info[key]}" for key, label in (("Title", "Title"), ("Genre", "Genre"),
                                                         ("Author", "Author")) if info.get(key)]
        if project.summary.get("Sentence"):
            bits.append(f"Summary: {project.summary['Sentence']}")
        if bits:
            out.append(("book", "Book info", "\n".join(bits)))
    return out


def fit(items: list[tuple[str, str, str]], max_tokens: int) -> str:
    """Join the parts in reading order within a token budget. An oversized scene keeps its
    END (what was just written matters most) when there is room for a useful amount of it."""
    chosen, used = [], 0
    for key, heading, text in items:
        text = (text or "").strip()
        if not text:
            continue
        cost = estimateTokens(text) + 8
        if used + cost > max_tokens:
            room = max_tokens - used - 8
            if key in ("scene", "selection") and room > 200:
                text = "[...]" + text[-int(room * 3.5):]
                cost = estimateTokens(text) + 8
            else:
                continue
        chosen.append((key, heading, text))
        used += cost
    chosen.sort(key=lambda p: ORDER.index(p[0]) if p[0] in ORDER else len(ORDER))
    return "\n\n".join(f"### {heading}\n{text}" for _k, heading, text in chosen)


def build(project: Project, sources: dict[str, bool], scene_id: int | None, max_tokens: int) -> str:
    return fit(parts(project, sources, scene_id), max_tokens)
