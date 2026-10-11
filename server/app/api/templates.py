"""Project templates: save a project's structure as a reusable starting point."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app import projects as store
from app.auth.deps import current_user
from app.schemas import ProjectName, TemplateList, TrashedOut

router = APIRouter(prefix="/api/templates", tags=["templates"], dependencies=[Depends(current_user)])


class NewTemplate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    from_project: str = Field(min_length=1, max_length=100)
    keep_text: bool = False  # False: scenes are emptied, only the structure is kept


@router.get("", response_model=TemplateList)
def list_templates():
    return {"templates": store.list_templates()}


@router.post("", status_code=201, response_model=ProjectName)
def create_template(body: NewTemplate):
    store.create_template(body.name, body.from_project, body.keep_text)
    return {"name": body.name}


@router.delete("/{name}", response_model=TrashedOut)
def delete_template(name: str):
    return {"ok": True, "trashed_as": store.delete_template(name)}
