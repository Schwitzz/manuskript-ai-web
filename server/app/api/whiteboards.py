"""Project whiteboards: multiple named whiteboards stored in `<project>/whiteboards.json`."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from app import projects as store
from app.auth.deps import current_user
from app.schemas import WhiteboardBoard, WhiteboardsData, WhiteboardViewport

router = APIRouter(
    prefix="/api/projects/{name}/whiteboards",
    tags=["whiteboards"],
    dependencies=[Depends(current_user)],
)

WHITEBOARDS_FILE = "whiteboards.json"


def _default_whiteboards() -> WhiteboardsData:
    return WhiteboardsData(
        active_board_id="default",
        boards=[
            WhiteboardBoard(
                id="default",
                name="Main Board",
                nodes=[],
                edges=[],
                viewport=WhiteboardViewport(x=0.0, y=0.0, zoom=1.0),
                show_all_notes=False,
            )
        ],
    )


def _parse_whiteboards(raw: str) -> WhiteboardsData:
    if not raw or not raw.strip():
        return _default_whiteboards()
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or not data.get("boards"):
            return _default_whiteboards()
        parsed = WhiteboardsData.model_validate(data)
        board_ids = {b.id for b in parsed.boards}
        if parsed.active_board_id not in board_ids:
            parsed.active_board_id = parsed.boards[0].id
        return parsed
    except Exception:
        return _default_whiteboards()


@router.get("", response_model=WhiteboardsData)
def get_whiteboards(name: str):
    with store.open_project(name) as p:
        raw = p.files.get(WHITEBOARDS_FILE, "")
        return _parse_whiteboards(raw if isinstance(raw, str) else "")


@router.put("", response_model=WhiteboardsData)
def save_whiteboards(name: str, body: WhiteboardsData):
    board_ids = [b.id for b in body.boards]
    if len(set(board_ids)) != len(board_ids):
        raise HTTPException(400, "Duplicate board IDs are not allowed")
    if body.active_board_id not in board_ids:
        body.active_board_id = body.boards[0].id
    with store.open_project(name) as p:
        serialized = json.dumps(body.model_dump(), indent=2)
        p.files_pending[WHITEBOARDS_FILE] = serialized  # type: ignore[assignment]
        p.save()
        return body
