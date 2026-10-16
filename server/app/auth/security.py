"""Password hashing, signed sessions, CSRF tokens, TOTP, rate limiting."""

import hashlib
import hmac
import json
import secrets
import time

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import get_settings
from app.db import db

SESSION_COOKIE = "msk_session"
CSRF_COOKIE = "msk_csrf"
CSRF_HEADER = "x-csrf-token"

_hasher = PasswordHasher()  # Argon2id by default

# Rate limit: failures inside WINDOW seconds before a lockout kicks in.
WINDOW = 15 * 60
FREE_FAILURES = 3
MAX_DELAY = 15 * 60


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def hash_password_pbkdf2(password: str, iterations: int = 310000) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return f"$pbkdf2-sha256${iterations}${salt}${dk.hex()}"


def verify_password(hashed: str, password: str) -> bool:
    if hashed.startswith("$pbkdf2-sha256$"):
        try:
            _, _, iter_s, salt_hex, dk_hex = hashed.split("$", 4)
            dk = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iter_s)
            )
            return hmac.compare_digest(dk.hex(), dk_hex)
        except Exception:
            return False
    try:
        return _hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt="msk-session")


def make_session(user_id: int, totp_pending: bool = False) -> str:
    return _serializer().dumps({"u": user_id, "p": totp_pending, "c": secrets.token_urlsafe(16)})


def read_session(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        return _serializer().loads(token, max_age=get_settings().session_hours * 3600)
    except BadSignature:
        return None


def csrf_for(session_token: str) -> str:
    key = get_settings().secret_key.encode()
    return hmac.new(key, session_token.encode(), hashlib.sha256).hexdigest()


def csrf_valid(session_token: str | None, supplied: str | None) -> bool:
    if not session_token or not supplied:
        return False
    return hmac.compare_digest(csrf_for(session_token), supplied)


# ---- TOTP ----

def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, username: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="Manuskript AI")


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=1)


def new_recovery_codes(n: int = 10) -> list[str]:
    return [secrets.token_hex(4) + "-" + secrets.token_hex(4) for _ in range(n)]


def hash_recovery(code: str) -> str:
    return hashlib.sha256(code.strip().lower().encode()).hexdigest()


def store_recovery_codes(codes: list[str]) -> str:
    return json.dumps([hash_recovery(c) for c in codes])


def use_recovery_code(stored_json: str, code: str) -> str | None:
    """Return updated stored JSON if the code matched (and is now spent), else None."""
    hashes = json.loads(stored_json)
    h = hash_recovery(code)
    if h not in hashes:
        return None
    hashes.remove(h)
    return json.dumps(hashes)


# ---- Rate limiting (per IP and per account) ----

def _failures(key: str, now: float) -> list[float]:
    with db() as conn:
        conn.execute("DELETE FROM login_attempt WHERE at < ?", (now - WINDOW,))
        rows = conn.execute(
            "SELECT at FROM login_attempt WHERE key = ? ORDER BY at", (key,)
        ).fetchall()
    return [r["at"] for r in rows]


def lockout_seconds(key: str, now: float | None = None) -> int:
    """Seconds the caller must still wait for this key (0 = allowed)."""
    now = now or time.time()
    fails = _failures(key, now)
    if len(fails) < FREE_FAILURES:
        return 0
    delay = min(2 ** (len(fails) - FREE_FAILURES + 1) * 5, MAX_DELAY)
    return max(0, int(fails[-1] + delay - now))


def record_failure(key: str, now: float | None = None) -> None:
    with db() as conn:
        conn.execute("INSERT INTO login_attempt(key, at) VALUES (?, ?)", (key, now or time.time()))


def clear_failures(key: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM login_attempt WHERE key = ?", (key,))
