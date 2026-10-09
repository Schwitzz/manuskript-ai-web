"""Plots (with steps and character links) and the world tree."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import projects as store
from app.auth.deps import current_user
from msklib.xmlrecords import Plot, WorldItem

router = APIRouter(prefix="/api/projects/{name}", tags=["plots-world"],
                   dependencies=[Depends(current_user)])


class StepIn(BaseModel):
    name: str = ""
    meta: str = ""
    summary: str = ""


class PlotIn(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    importance: str = Field(default="0", pattern="^[0-2]$")
    description: str = ""
    result: str = ""
    summary: str = ""
    characters: list[int] = []
    steps: list[StepIn] = []


class WorldIn(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str = ""
    passion: str = ""
    conflict: str = ""
    parent_id: int | None = None


class WorldFields(BaseModel):
    name: str | None = None
    description: str | None = None
    passion: str | None = None
    conflict: str | None = None


def _plot_out(pl: Plot) -> dict:
    return {"id": pl.id, "name": pl.name, "importance": pl.attrs.get("importance", "0"),
            "description": pl.attrs.get("description", ""), "result": pl.attrs.get("result", ""),
            "summary": pl.attrs.get("summary", ""), "characters": pl.characters,
            "steps": [{"id": int(s.get("ID", "0") or 0), "name": s.get("name", ""),
                       "meta": s.get("meta", ""), "summary": s.get("summary", "")}
                      for s in pl.steps]}


def _apply_plot(pl: Plot, body: PlotIn, known_chars: set[int]) -> None:
    if any(c not in known_chars for c in body.characters):
        raise HTTPException(400, "Unknown character in plot")
    for key in ("name", "importance", "description", "result", "summary"):
        pl.attrs[key] = getattr(body, key)
    pl.set_characters(body.characters)
    pl.steps = [{"name": s.name, "ID": str(i), "meta": s.meta, "summary": s.summary}
                for i, s in enumerate(body.steps)]
    if pl.steps:
        pl.attrs["steps"] = "Resolution steps"
    else:
        pl.attrs.pop("steps", None)


def _find_plot(p, plot_id: int) -> Plot:
    pl = next((x for x in p.plots if x.id == plot_id), None)
    if pl is None:
        raise HTTPException(404, "Plot not found")
    return pl


@router.get("/plots")
def list_plots(name: str):
    with store.open_project(name) as p:
        return {"plots": [_plot_out(x) for x in p.plots]}


@router.post("/plots", status_code=201)
def create_plot(name: str, body: PlotIn):
    with store.open_project(name) as p:
        pl = Plot(attrs={"ID": str(max([x.id for x in p.plots] + [-1]) + 1)})
        _apply_plot(pl, body, {c.id for c in p.characters})
        p.plots.append(pl)
        p.save()
        return _plot_out(pl)


@router.put("/plots/{plot_id}")
def update_plot(name: str, plot_id: int, body: PlotIn):
    with store.open_project(name) as p:
        pl = _find_plot(p, plot_id)
        _apply_plot(pl, body, {c.id for c in p.characters})
        p.save()
        return _plot_out(pl)


@router.delete("/plots/{plot_id}")
def delete_plot(name: str, plot_id: int):
    with store.open_project(name) as p:
        p.plots.remove(_find_plot(p, plot_id))
        p.save()
        return {"ok": True}


def _world_out(item: WorldItem) -> dict:
    return {"id": item.id, "name": item.name,
            "description": item.attrs.get("description", ""),
            "passion": item.attrs.get("passion", ""), "conflict": item.attrs.get("conflict", ""),
            "children": [_world_out(c) for c in item.children]}


def _find_world(p, item_id: int) -> tuple[WorldItem, list[WorldItem]]:
    def search(items):
        for it in items:
            if it.id == item_id:
                return it, items
            found = search(it.children)
            if found:
                return found
        return None
    found = search(p.world)
    if not found:
        raise HTTPException(404, "World item not found")
    return found


@router.get("/world")
def get_world(name: str):
    with store.open_project(name) as p:
        return {"items": [_world_out(i) for i in p.world]}


@router.post("/world", status_code=201)
def create_world_item(name: str, body: WorldIn):
    with store.open_project(name) as p:
        ids = [i.id for i in p.world] + [i.id for r in p.world for i in r.walk()]
        item = WorldItem(attrs={"name": body.name, "ID": str(max(ids + [-1]) + 1)})
        for key in ("description", "passion", "conflict"):
            if getattr(body, key):
                item.attrs[key] = getattr(body, key)
        siblings = p.world if body.parent_id is None else _find_world(p, body.parent_id)[0].children
        siblings.append(item)
        p.save()
        return _world_out(item)


@router.patch("/world/{item_id}")
def update_world_item(name: str, item_id: int, body: WorldFields):
    with store.open_project(name) as p:
        item, _ = _find_world(p, item_id)
        for k, v in body.model_dump(exclude_unset=True).items():
            if v:
                item.attrs[k] = v
            elif k != "name":
                item.attrs.pop(k, None)
        p.save()
        return _world_out(item)


@router.delete("/world/{item_id}")
def delete_world_item(name: str, item_id: int):
    with store.open_project(name) as p:
        item, siblings = _find_world(p, item_id)
        siblings.remove(item)
        p.save()
        return {"ok": True}
