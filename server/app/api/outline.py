"""Outline editing: create, rename, move, delete, and per-item fields."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import projects as store
from app.auth.deps import current_user
from app.schemas import Ok, OutlineItemOut
from msklib.model import Item

router = APIRouter(prefix="/api/projects/{name}/outline", tags=["outline"],
                   dependencies=[Depends(current_user)])

# Item fields the browser may set, mapped to the key stored in the file.
FIELDS = {"label": "label", "status": "status", "compile": "compile", "pov": "POV",
          "summary_sentence": "summarySentence", "summary_full": "summaryFull",
          "notes": "notes", "goal": "setGoal"}


class NewItem(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    type: str = Field(default="md", pattern="^(md|folder)$")
    parent_id: int | None = None  # None = top level
    position: int | None = None   # None = append


class MoveItem(BaseModel):
    parent_id: int | None = None
    position: int = Field(ge=0)


class Rename(BaseModel):
    title: str = Field(min_length=1, max_length=300)


class Fields(BaseModel):
    label: str | None = None
    status: str | None = None
    compile: str | None = None
    pov: str | None = None
    summary_sentence: str | None = None
    summary_full: str | None = None
    notes: str | None = None
    goal: str | None = None


def _item(p, item_id: int) -> Item:
    item = p.find(item_id)
    if item is None:
        raise HTTPException(404, "Item not found")
    return item


def _parent(p, parent_id: int | None) -> Item:
    if parent_id is None:
        return p.outline
    parent = _item(p, parent_id)
    if not parent.is_folder:
        raise HTTPException(400, "Items can only be placed inside folders")
    return parent


def _detach(item: Item) -> None:
    item.parent.children.remove(item)


def _attach(item: Item, parent: Item, position: int | None) -> None:
    item.parent = parent
    if position is None or position >= len(parent.children):
        parent.children.append(item)
    else:
        parent.children.insert(max(position, 0), item)


@router.post("", status_code=201, response_model=OutlineItemOut)
def create_item(name: str, body: NewItem):
    with store.open_project(name) as p:
        item = Item(id=p.next_id(), title=body.title, type=body.type, meta={"compile": "2"})
        _attach(item, _parent(p, body.parent_id), body.position)
        p.save()
        return store.item_summary(item)


@router.patch("/{item_id}/title", response_model=OutlineItemOut)
def rename_item(name: str, item_id: int, body: Rename):
    with store.open_project(name) as p:
        item = _item(p, item_id)
        item.title = body.title
        p.save()
        return store.item_summary(item)


@router.post("/{item_id}/move", response_model=Ok)
def move_item(name: str, item_id: int, body: MoveItem):
    with store.open_project(name) as p:
        item = _item(p, item_id)
        parent = _parent(p, body.parent_id)
        node = parent
        while node is not None:  # a folder can never be moved into itself or its own children
            if node is item:
                raise HTTPException(400, "Cannot move a folder into itself")
            node = node.parent
        _detach(item)
        _attach(item, parent, body.position)
        p.save()
        return {"ok": True}


@router.patch("/{item_id}/fields", response_model=OutlineItemOut)
def set_fields(name: str, item_id: int, body: Fields):
    with store.open_project(name) as p:
        item = _item(p, item_id)
        changes = body.model_dump(exclude_unset=True)
        # Desktop stores label and status as 1-based positions in labels.txt / status.txt
        # ("" or "0" = none). A name here would be read by desktop as "no label", so refuse it.
        for attr, known in (("label", p.labels), ("status", p.status)):
            value = changes.get(attr)
            if value not in (None, ""):
                if not value.isdigit() or int(value) > len(known):
                    raise HTTPException(
                        422, f"{attr} must be a number from 0 to {len(known)} (its position in the list)")
        for attr, value in changes.items():
            key = FIELDS[attr]
            if value in (None, ""):
                item.meta.pop(key, None)
            else:
                item.meta[key] = str(value)
        p.save()
        return store.item_summary(item)


@router.delete("/{item_id}", response_model=Ok)
def delete_item(name: str, item_id: int):
    """Moves the item (and anything inside it) to .trash; nothing is hard deleted."""
    with store.open_project(name) as p:
        item = _item(p, item_id)
        _detach(item)
        p.save()
        return {"ok": True}
