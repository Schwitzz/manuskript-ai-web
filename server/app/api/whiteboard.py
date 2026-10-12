"""Whiteboard (flow diagram) layout storage.

The layout is stored as JSON in the project's dot-folder `.whiteboards/layout.json`.
Dot-folders are invisible to desktop Manuskript (it skips them on load and save),
and the web server's msklib also ignores them.  So the layout survives round-trips
with the desktop app without any special handling.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import projects as store
from app.auth.deps import current_user

router = APIRouter(prefix="/api/projects", tags=["whiteboard"],
                   dependencies=[Depends(current_user)])

MAX_LAYOUT = 5 * 1024 * 1024  # 5 MB cap


class WhiteboardLayout(BaseModel):
    version: int = 1
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)
    viewport: dict = Field(default_factory=lambda: {"x": 0, "y": 0, "zoom": 1})


def _layout_path(name: str) -> Path:
    project_dir = store.project_path(name)
    if not (project_dir / "MANUSKRIPT").exists():
        raise HTTPException(404, "Project not found")
    wb_dir = project_dir / ".whiteboards"
    return wb_dir / "layout.json"


@router.get("/{name}/whiteboard", response_model=WhiteboardLayout)
def get_whiteboard(name: str):
    path = _layout_path(name)
    if not path.exists():
        return WhiteboardLayout()
    try:
        data = json.loads(path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return WhiteboardLayout()
    return WhiteboardLayout(**data)


@router.put("/{name}/whiteboard", response_model=WhiteboardLayout)
def put_whiteboard(name: str, body: WhiteboardLayout):
    path = _layout_path(name)
    raw = json.dumps(body.model_dump(), separators=(",", ":"))
    if len(raw.encode("utf-8")) > MAX_LAYOUT:
        raise HTTPException(413, "Whiteboard layout too large")
    with store._lock_for(name):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw, "utf-8")
    return body