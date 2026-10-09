"""GET /api/events: Server-Sent Events so open tabs refresh when a project changes."""

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app import events
from app.auth.deps import current_user

router = APIRouter(prefix="/api", tags=["events"], dependencies=[Depends(current_user)])
HEARTBEAT = 15.0


async def stream(request: Request, heartbeat: float):
    q = events.subscribe()
    try:
        yield "retry: 3000\n\nevent: hello\ndata: {}\n\n"
        while not await request.is_disconnected():
            try:
                ev = await asyncio.wait_for(q.get(), timeout=heartbeat)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"  # keeps proxies from closing an idle stream
                continue
            yield f"event: {ev['type']}\ndata: {json.dumps(ev)}\n\n"
    finally:
        events.unsubscribe(q)


@router.get("/events")
async def events_stream(request: Request):
    return StreamingResponse(stream(request, HEARTBEAT), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
