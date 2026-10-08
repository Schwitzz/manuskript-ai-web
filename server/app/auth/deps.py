"""FastAPI dependencies: current user and CSRF enforcement."""

from fastapi import HTTPException, Request

from app.auth import security as sec
from app.db import db

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def enforce_csrf(request: Request) -> None:
    if request.method in SAFE_METHODS:
        return
    token = request.cookies.get(sec.SESSION_COOKIE)
    if not sec.csrf_valid(token, request.headers.get(sec.CSRF_HEADER)):
        raise HTTPException(403, "Bad or missing CSRF token")


def current_user(request: Request) -> dict:
    """Fully authenticated user (TOTP completed if enabled)."""
    enforce_csrf(request)
    data = sec.read_session(request.cookies.get(sec.SESSION_COOKIE))
    if not data or data.get("p"):
        raise HTTPException(401, "Not authenticated")
    with db() as conn:
        row = conn.execute("SELECT * FROM user WHERE id = ?", (data["u"],)).fetchone()
    if not row:
        raise HTTPException(401, "Not authenticated")
    return dict(row)
