"""Characters, labels, statuses, book info and summaries."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import projects as store
from app.auth.deps import current_user
from msklib.records import Character, Label

router = APIRouter(prefix="/api/projects/{name}", tags=["records"],
                   dependencies=[Depends(current_user)])

COLOR = "^#[0-9a-fA-F]{6}$"


class CharacterIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    importance: str = Field(default="0", pattern="^[0-2]$")
    pov: str = ""
    motivation: str = ""
    goal: str = ""
    conflict: str = ""
    epiphany: str = ""
    summary_sentence: str = ""
    summary_para: str = ""
    summary_full: str = ""
    notes: str = ""
    color: str = Field(default="#000000", pattern=COLOR)
    infos: list[tuple[str, str]] = []


class LabelIn(BaseModel):
    name: str = Field(min_length=1, max_length=19)  # the file pads names to 20 columns
    color: str = Field(default="", pattern="^(#[0-9a-fA-F]{6})?$")


class LabelsIn(BaseModel):
    labels: list[LabelIn]


class StatusIn(BaseModel):
    status: list[str]


class KeyedIn(BaseModel):
    values: dict[str, str]


def _char(c: Character) -> dict:
    d = asdict(c)
    d.pop("last_path")
    return d


def _find_char(p, char_id: int) -> Character:
    c = next((c for c in p.characters if c.id == char_id), None)
    if c is None:
        raise HTTPException(404, "Character not found")
    return c


@router.get("/characters")
def list_characters(name: str):
    with store.open_project(name) as p:
        return {"characters": [_char(c) for c in p.characters]}


@router.post("/characters", status_code=201)
def create_character(name: str, body: CharacterIn):
    with store.open_project(name) as p:
        c = Character(id=max([c.id for c in p.characters] + [-1]) + 1, **body.model_dump())
        p.characters.append(c)
        p.save()
        return _char(c)


@router.put("/characters/{char_id}")
def update_character(name: str, char_id: int, body: CharacterIn):
    with store.open_project(name) as p:
        c = _find_char(p, char_id)
        for k, v in body.model_dump().items():
            setattr(c, k, v)
        p.save()
        return _char(c)


@router.delete("/characters/{char_id}")
def delete_character(name: str, char_id: int):
    with store.open_project(name) as p:
        c = _find_char(p, char_id)
        p.characters.remove(c)
        for plot in p.plots:  # keep plot links valid
            if char_id in plot.characters:
                plot.set_characters([i for i in plot.characters if i != char_id])
        p.save()
        return {"ok": True}


@router.get("/labels")
def get_labels(name: str):
    with store.open_project(name) as p:
        return {"labels": [asdict(lb) for lb in p.labels], "status": p.status}


@router.put("/labels")
def set_labels(name: str, body: LabelsIn):
    with store.open_project(name) as p:
        p.labels = [Label(lb.name, lb.color) for lb in body.labels]
        p.save()
        return {"labels": [asdict(lb) for lb in p.labels]}


@router.put("/status")
def set_status(name: str, body: StatusIn):
    with store.open_project(name) as p:
        p.status = [s for s in body.status if s.strip()]
        p.save()
        return {"status": p.status}


@router.get("/info")
def get_info(name: str):
    with store.open_project(name) as p:
        return {"info": p.infos, "summary": p.summary}


@router.put("/info")
def set_info(name: str, body: KeyedIn):
    with store.open_project(name) as p:
        p.infos = {k: v for k, v in body.values.items() if v.strip()}
        p.save()
        return {"info": p.infos}


@router.put("/summary")
def set_summary(name: str, body: KeyedIn):
    with store.open_project(name) as p:
        p.summary = {k: v for k, v in body.values.items() if v.strip()}
        p.save()
        return {"summary": p.summary}
