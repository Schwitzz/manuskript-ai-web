import pyotp

from tests.conftest import csrf_headers

PW = "correct horse battery"


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_status_before_setup(client):
    r = client.get("/api/auth/status").json()
    assert r == {"setup_required": True, "authenticated": False, "totp_pending": False}


def test_setup_only_once_and_short_password_rejected(client):
    assert client.post("/api/auth/setup", json={"username": "ab", "password": "short"}).status_code == 422
    assert client.post("/api/auth/setup", json={"username": "ab", "password": PW}).status_code == 200
    assert client.post("/api/auth/setup", json={"username": "x", "password": PW}).status_code == 409


def test_me_requires_login(client):
    assert client.get("/api/auth/me").status_code == 401


def test_setup_logs_in_and_me_works(logged_in):
    assert logged_in.get("/api/auth/me").json()["username"] == "ab"


def test_cookie_flags(client):
    r = client.post("/api/auth/setup", json={"username": "ab", "password": PW})
    cookie = r.headers.get_list("set-cookie")[0].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_csrf_required_on_post(logged_in):
    assert logged_in.post("/api/auth/totp/setup").status_code == 403
    assert logged_in.post("/api/auth/totp/setup", headers=csrf_headers(logged_in)).status_code == 200


def test_logout_then_login(logged_in):
    assert logged_in.post("/api/auth/logout").status_code == 403
    assert logged_in.post("/api/auth/logout", headers=csrf_headers(logged_in)).status_code == 200
    logged_in.cookies.clear()
    assert logged_in.get("/api/auth/me").status_code == 401
    r = logged_in.post("/api/auth/login", json={"username": "ab", "password": PW})
    assert r.status_code == 200 and r.json()["totp_required"] is False
    assert logged_in.get("/api/auth/me").status_code == 200


def test_wrong_password_and_rate_limit(logged_in):
    logged_in.cookies.clear()
    for _ in range(3):
        r = logged_in.post("/api/auth/login", json={"username": "ab", "password": "nope"})
        assert r.status_code == 401
    r = logged_in.post("/api/auth/login", json={"username": "ab", "password": PW})
    assert r.status_code == 429 and "retry-after" in r.headers


def test_totp_flow(logged_in):
    h = csrf_headers(logged_in)
    setup = logged_in.post("/api/auth/totp/setup", headers=h).json()
    assert setup["qr_svg_base64"]
    assert logged_in.post("/api/auth/totp/enable", json={"code": "000000"}, headers=h).status_code == 400
    code = pyotp.TOTP(setup["secret"]).now()
    enabled = logged_in.post("/api/auth/totp/enable", json={"code": code}, headers=h).json()
    assert len(enabled["recovery_codes"]) == 10

    logged_in.cookies.clear()
    r = logged_in.post("/api/auth/login", json={"username": "ab", "password": PW})
    assert r.json()["totp_required"] is True
    assert logged_in.get("/api/auth/me").status_code == 401  # pending session is not enough
    h = csrf_headers(logged_in)
    assert logged_in.post("/api/auth/totp/verify", json={"code": "111111"}, headers=h).status_code == 401
    ok = logged_in.post("/api/auth/totp/verify", json={"code": enabled["recovery_codes"][0]}, headers=h)
    assert ok.status_code == 200
    assert logged_in.get("/api/auth/me").status_code == 200

    # a recovery code works only once
    logged_in.cookies.clear()
    logged_in.post("/api/auth/login", json={"username": "ab", "password": PW})
    h = csrf_headers(logged_in)
    again = logged_in.post("/api/auth/totp/verify", json={"code": enabled["recovery_codes"][0]}, headers=h)
    assert again.status_code == 401


def test_register_requires_auth(client):
    # No session cookie at all: CSRF enforcement (which runs first) rejects with 403.
    assert client.post("/api/auth/register", json={"username": "bob", "password": PW}).status_code == 403


def test_register_creates_user_without_switching_session(logged_in):
    h = csrf_headers(logged_in)
    r = logged_in.post("/api/auth/register", json={"username": "bob", "password": PW}, headers=h)
    assert r.status_code == 200
    # The admin's own session must be untouched: still logged in as "ab".
    assert logged_in.get("/api/auth/me").json()["username"] == "ab"
    # The new user can log in with their own credentials.
    logged_in.cookies.clear()
    r = logged_in.post("/api/auth/login", json={"username": "bob", "password": PW})
    assert r.status_code == 200
    assert logged_in.get("/api/auth/me").json()["username"] == "bob"


def test_register_duplicate_username_rejected(logged_in):
    h = csrf_headers(logged_in)
    logged_in.post("/api/auth/register", json={"username": "bob", "password": PW}, headers=h)
    # case-insensitive duplicate check
    r = logged_in.post("/api/auth/register", json={"username": "BOB", "password": PW}, headers=h)
    assert r.status_code == 409


def test_cidr_allowlist(client, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("MSK_LOGIN_ALLOW_CIDRS", "10.0.0.0/8")
    get_settings.cache_clear()
    r = client.post("/api/auth/setup", json={"username": "ab", "password": PW})
    assert r.status_code == 403  # TestClient peer is not in 10.0.0.0/8
