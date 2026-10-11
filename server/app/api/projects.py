"""Projects, outline tree and documents."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import projects as store
from app.auth.deps import current_user
from app.schemas import SampleList, DocumentOut, OutlineOut, ProjectList, ProjectName, SavedOut
from msklib.counts import item_counts, word_count

router = APIRouter(prefix="/api/projects", tags=["projects"], dependencies=[Depends(current_user)])


class NewProject(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    title: str = Field(default="", max_length=200)
    author: str = Field(default="", max_length=200)
    sample: str | None = Field(default=None, max_length=100)  # copy a bundled sample instead
    template: str | None = Field(default=None, max_length=100)  # or copy a user template


class SaveDocument(BaseModel):
    text: str
    base_version: str  # the version the browser last loaded; a mismatch means a stale save


@router.get("", response_model=ProjectList)
def list_projects():
    return {"projects": store.list_projects()}


@router.post("", status_code=201, response_model=ProjectName)
def create_project(body: NewProject):
    if body.sample and body.template:
        raise HTTPException(400, "Choose either a sample or a template, not both")
    if body.sample:
        store.create_from_sample(body.name, body.sample)
    elif body.template:
        store.create_from_template(body.name, body.template, body.title or body.name)
    else:
        store.create_project(body.name, body.title or body.name, body.author)
    return {"name": body.name}


@router.get("/samples", response_model=SampleList)
def list_samples():
    return {"samples": store.list_samples()}


@router.get("/{name}/outline", response_model=OutlineOut)
def outline(name: str):
    with store.open_project(name) as p:
        words, chars = item_counts(p.outline)
        return {"title": p.infos.get("Title", name), "words": words, "chars": chars,
                "items": [store.item_summary(c) for c in p.outline.children]}


@router.get("/{name}/documents/{item_id}", response_model=DocumentOut)
def read_document(name: str, item_id: int):
    with store.open_project(name) as p:
        item = p.find(item_id)
        if item is None or item.is_folder:
            raise HTTPException(404, "Document not found")
        return {"id": item.id, "title": item.title, "text": item.text,
                "version": store.doc_version(item), "words": word_count(item.text)}


@router.put("/{name}/documents/{item_id}", response_model=SavedOut)
def save_document(name: str, item_id: int, body: SaveDocument):
    with store.open_project(name) as p:
        item = p.find(item_id)
        if item is None or item.is_folder:
            raise HTTPException(404, "Document not found")
        current = store.doc_version(item)
        if body.base_version != current:
            # Never overwrite: hand back what is on disk so the browser can offer a merge.
            raise HTTPException(409, detail={"message": "The document changed since you opened it",
                                             "version": current, "text": item.text})
        if body.text != item.text:
            item.text = body.text
            p.save()
        return {"version": store.doc_version(item), "words": word_count(item.text)}
