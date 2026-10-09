"""Cross references: what mentions a character, scene, plot or world item."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from app import projects as store
from app.auth.deps import current_user
from app.schemas import BacklinksOut, BrokenRefsOut
from msklib import references

router = APIRouter(prefix="/api/projects/{name}/references", tags=["references"],
                   dependencies=[Depends(current_user)])


@router.get("/broken", response_model=BrokenRefsOut)
def broken(name: str):
    with store.open_project(name) as p:
        return {"broken": references.broken(p)}


@router.get("/{kind}/{item_id}", response_model=BacklinksOut)
def backlinks(name: str, kind: Literal["scene", "character", "plot", "world"], item_id: int):
    with store.open_project(name) as p:
        title = references.title_of(p, kind, item_id)
        if title is None:
            raise HTTPException(404, "Not found")
        return {"target_title": title, "backlinks": references.backlinks(p, kind, item_id)}
