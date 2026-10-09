"""Scene revision history: list, read, restore."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import projects as store
from app.auth.deps import current_user
from app.schemas import RestoredOut, RevisionOut, RevisionsOut
from msklib.counts import word_count
from msklib.revisions import Revisions

router = APIRouter(prefix="/api/projects/{name}/documents/{item_id}/revisions",
                   tags=["revisions"], dependencies=[Depends(current_user)])


class Restore(BaseModel):
    base_version: str  # same stale-save protection as a normal save


def _revs(p, item_id: int):
    item = p.find(item_id)
    if item is None or item.is_folder:
        raise HTTPException(404, "Document not found")
    raw = p.files.get("revisions.xml")
    return item, Revisions(raw if isinstance(raw, bytes) else None).get(item_id)


@router.get("", response_model=RevisionsOut)
def list_revisions(name: str, item_id: int):
    with store.open_project(name) as p:
        _item, revs = _revs(p, item_id)
        return {"revisions": [{"timestamp": ts, "words": word_count(text)}
                              for ts, text in sorted(revs, reverse=True)]}


@router.get("/{timestamp}", response_model=RevisionOut)
def read_revision(name: str, item_id: int, timestamp: int):
    with store.open_project(name) as p:
        _item, revs = _revs(p, item_id)
        for ts, text in revs:
            if ts == timestamp:
                return {"timestamp": ts, "text": text}
        raise HTTPException(404, "Revision not found")


@router.post("/{timestamp}/restore", response_model=RestoredOut)
def restore_revision(name: str, item_id: int, timestamp: int, body: Restore):
    with store.open_project(name) as p:
        item, revs = _revs(p, item_id)
        text = next((t for ts, t in revs if ts == timestamp), None)
        if text is None:
            raise HTTPException(404, "Revision not found")
        current = store.doc_version(item)
        if body.base_version != current:
            raise HTTPException(409, detail={"message": "The document changed since you opened it",
                                             "version": current, "text": item.text})
        item.text = text  # saving keeps the replaced text as a new revision
        p.save()
        return {"version": store.doc_version(item), "text": text}
