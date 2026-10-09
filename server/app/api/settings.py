"""Project settings that matter to the web app. The rest of settings.txt (desktop window
state, fonts, view columns) is left exactly as the desktop wrote it."""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app import projects as store
from app.auth.deps import current_user
from app.schemas import SettingsOut
from msklib.revisions import DEFAULT_RULES

router = APIRouter(prefix="/api/projects/{name}/settings", tags=["settings"],
                   dependencies=[Depends(current_user)])


class RevisionRules(BaseModel):
    keep: bool = True
    smartremove: bool = True
    # {span in seconds, or "null" for everything older: minimum seconds between revisions}
    rules: dict[str, float] | None = None


class SettingsIn(BaseModel):
    countSpaces: bool | None = None
    viewMode: Literal["fiction", "nonfiction", "simple"] | None = None
    defaultTextType: Literal["md"] | None = None
    spell_dict: str | None = Field(default=None, alias="dict", max_length=20,
                                   pattern="^[A-Za-z_]*$")

    model_config = ConfigDict(populate_by_name=True)
    revisions: RevisionRules | None = None


def _view(settings: dict) -> dict:
    rev = settings.get("revisions", {})
    return {
        "countSpaces": settings.get("countSpaces", True),
        "viewMode": settings.get("viewMode", "fiction"),
        "defaultTextType": settings.get("defaultTextType", "md"),
        "dict": settings.get("dict", ""),
        "revisions": {
            "keep": rev.get("keep", True), "smartremove": rev.get("smartremove", True),
            "rules": rev.get("rules") or {("null" if k is None else str(k)): v
                                          for k, v in DEFAULT_RULES.items()}},
    }


@router.get("", response_model=SettingsOut, response_model_by_alias=True)
def get_settings(name: str):
    with store.open_project(name) as p:
        return _view(p.settings)


@router.patch("", response_model=SettingsOut, response_model_by_alias=True)
def update_settings(name: str, body: SettingsIn):
    with store.open_project(name) as p:
        for key, value in body.model_dump(exclude_unset=True, by_alias=True).items():
            if key == "revisions":
                current = p.settings.get("revisions", {})
                current.update({k: v for k, v in value.items() if v is not None})
                p.settings["revisions"] = current
            else:
                p.settings[key] = value
        p.save()
        return _view(p.settings)
