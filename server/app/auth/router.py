"""Auth endpoints: first-run setup, login, TOTP, logout."""

import base64
import io

import qrcode
import qrcode.image.svg
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth import security as sec
from app.auth.deps import current_user, enforce_csrf
from app.auth.netutil import client_ip, ip_allowed, request_is_https
from app.config import get_settings
from app.db import db
from app.schemas import AuthStatusOut, LoginOut, MeOut, Ok, RecoveryCodesOut, TotpSetupOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class SetupBody(Credentials):
    password: str = Field(min_length=10, max_length=256)


class CodeBody(BaseModel):
    code: str = Field(min_length=1, max_length=32)


def _user_count() -> int:
    with db() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM user").fetchone()["n"]


def _set_session(request: Request, response: Response, token: str) -> None:
    secure = get_settings().cookie_secure and request_is_https(request)
    max_age = get_settings().session_hours * 3600
    response.set_cookie(sec.SESSION_COOKIE, token, max_age=max_age, httponly=True,
                        secure=secure, samesite="lax", path="/")
    # Readable by JS so the browser can echo it in the CSRF header.
    response.set_cookie(sec.CSRF_COOKIE, sec.csrf_for(token), max_age=max_age,
                        httponly=False, secure=secure, samesite="lax", path="/")


def _guard_login(request: Request, username: str) -> list[str]:
    ip = client_ip(request)
    if not ip_allowed(ip):
        raise HTTPException(403, "Login not allowed from this address")
    keys = ["ip:" + ip, "user:" + username.lower()]
    wait = max(sec.lockout_seconds(k) for k in keys)
    if wait:
        raise HTTPException(429, f"Too many attempts. Try again in {wait} seconds",
                            headers={"Retry-After": str(wait)})
    return keys


@router.get("/status", response_model=AuthStatusOut)
def status(request: Request):
    data = sec.read_session(request.cookies.get(sec.SESSION_COOKIE))
    return {
        "setup_required": _user_count() == 0,
        "authenticated": bool(data and not data.get("p")),
        "totp_pending": bool(data and data.get("p")),
    }


@router.post("/setup", response_model=Ok)
def setup(body: SetupBody, request: Request, response: Response):
    if not ip_allowed(client_ip(request)):
        raise HTTPException(403, "Setup not allowed from this address")
    with db() as conn:
        if conn.execute("SELECT COUNT(*) AS n FROM user").fetchone()["n"]:
            raise HTTPException(409, "An account already exists")
        cur = conn.execute(
            "INSERT INTO user(username, password_hash) VALUES (?, ?)",
            (body.username, sec.hash_password(body.password)))
        uid = cur.lastrowid
    _set_session(request, response, sec.make_session(uid))
    return {"ok": True}


@router.post("/login", response_model=LoginOut)
def login(body: Credentials, request: Request, response: Response):
    keys = _guard_login(request, body.username)
    with db() as conn:
        row = conn.execute("SELECT * FROM user WHERE username = ?", (body.username,)).fetchone()
    if not row or not sec.verify_password(row["password_hash"], body.password):
        for k in keys:
            sec.record_failure(k)
        raise HTTPException(401, "Wrong username or password")
    if row["totp_enabled"]:
        _set_session(request, response, sec.make_session(row["id"], totp_pending=True))
        return {"ok": True, "totp_required": True}
    for k in keys:
        sec.clear_failures(k)
    _set_session(request, response, sec.make_session(row["id"]))
    return {"ok": True, "totp_required": False}


@router.post("/totp/verify", response_model=Ok)
def totp_verify(body: CodeBody, request: Request, response: Response):
    enforce_csrf(request)
    data = sec.read_session(request.cookies.get(sec.SESSION_COOKIE))
    if not data or not data.get("p"):
        raise HTTPException(401, "No pending two-factor login")
    with db() as conn:
        row = conn.execute("SELECT * FROM user WHERE id = ?", (data["u"],)).fetchone()
    if not row:
        raise HTTPException(401, "Not authenticated")
    keys = _guard_login(request, row["username"])
    ok = sec.verify_totp(row["totp_secret"], body.code)
    if not ok:
        updated = sec.use_recovery_code(row["recovery_codes"], body.code)
        if updated is not None:
            ok = True
            with db() as conn:
                conn.execute("UPDATE user SET recovery_codes = ? WHERE id = ?", (updated, row["id"]))
    if not ok:
        for k in keys:
            sec.record_failure(k)
        raise HTTPException(401, "Wrong code")
    for k in keys:
        sec.clear_failures(k)
    _set_session(request, response, sec.make_session(row["id"]))
    return {"ok": True}


@router.post("/logout", response_model=Ok)
def logout(request: Request, response: Response):
    enforce_csrf(request)
    response.delete_cookie(sec.SESSION_COOKIE, path="/")
    response.delete_cookie(sec.CSRF_COOKIE, path="/")
    return {"ok": True}


@router.post("/totp/setup", response_model=TotpSetupOut)
def totp_setup(user: dict = Depends(current_user)):
    """Start enrolment: returns secret + QR. Not enforced until /totp/enable succeeds."""
    secret = sec.new_totp_secret()
    with db() as conn:
        conn.execute("UPDATE user SET totp_secret = ?, totp_enabled = 0 WHERE id = ?",
                     (secret, user["id"]))
    uri = sec.totp_uri(secret, user["username"])
    buf = io.BytesIO()
    qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage).save(buf)
    return {"secret": secret, "uri": uri,
            "qr_svg_base64": base64.b64encode(buf.getvalue()).decode()}


@router.post("/totp/enable", response_model=RecoveryCodesOut)
def totp_enable(body: CodeBody, user: dict = Depends(current_user)):
    if not user["totp_secret"] or not sec.verify_totp(user["totp_secret"], body.code):
        raise HTTPException(400, "Wrong code")
    codes = sec.new_recovery_codes()
    with db() as conn:
        conn.execute("UPDATE user SET totp_enabled = 1, recovery_codes = ? WHERE id = ?",
                     (sec.store_recovery_codes(codes), user["id"]))
    return {"ok": True, "recovery_codes": codes}  # shown once


@router.post("/totp/disable", response_model=Ok)
def totp_disable(body: CodeBody, user: dict = Depends(current_user)):
    if not user["totp_enabled"] or not sec.verify_totp(user["totp_secret"], body.code):
        raise HTTPException(400, "Wrong code")
    with db() as conn:
        conn.execute("UPDATE user SET totp_enabled = 0, totp_secret = NULL, "
                     "recovery_codes = '[]' WHERE id = ?", (user["id"],))
    return {"ok": True}


@router.get("/me", response_model=MeOut)
def me(user: dict = Depends(current_user)):
    return {"username": user["username"], "totp_enabled": bool(user["totp_enabled"])}
