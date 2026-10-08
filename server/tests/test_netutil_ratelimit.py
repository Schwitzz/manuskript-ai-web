import pytest
from starlette.requests import Request

from app.auth import security as sec
from app.auth.netutil import client_ip, ip_allowed, request_is_https
from app.config import get_settings
from app.db import init_db


def make_request(peer: str, headers: dict[str, str] | None = None, scheme: str = "http") -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw,
                    "client": (peer, 1234), "scheme": scheme, "query_string": b"",
                    "server": ("test", 80)})


@pytest.fixture()
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("MSK_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    init_db()
    yield monkeypatch
    get_settings.cache_clear()


def set_env(mp, **kw):
    for k, v in kw.items():
        mp.setenv("MSK_" + k.upper(), v)
    get_settings.cache_clear()


def test_forwarded_for_ignored_from_untrusted_peer(settings):
    req = make_request("9.9.9.9", {"x-forwarded-for": "1.2.3.4"})
    assert client_ip(req) == "9.9.9.9"


def test_forwarded_for_used_from_trusted_proxy(settings):
    set_env(settings, trusted_proxies="10.0.0.2")
    req = make_request("10.0.0.2", {"x-forwarded-for": "1.2.3.4"})
    assert client_ip(req) == "1.2.3.4"


def test_spoofed_left_hop_is_not_trusted(settings):
    set_env(settings, trusted_proxies="10.0.0.2,10.0.0.3")
    req = make_request("10.0.0.3", {"x-forwarded-for": "6.6.6.6, 1.2.3.4, 10.0.0.2"})
    assert client_ip(req) == "1.2.3.4"


def test_https_only_trusted_from_proxy(settings):
    plain = make_request("9.9.9.9", {"x-forwarded-proto": "https"})
    assert request_is_https(plain) is False
    set_env(settings, trusted_proxies="10.0.0.2")
    proxied = make_request("10.0.0.2", {"x-forwarded-proto": "https"})
    assert request_is_https(proxied) is True


def test_cidr_allowlist(settings):
    assert ip_allowed("8.8.8.8") is True  # empty list allows all
    set_env(settings, login_allow_cidrs="192.168.0.0/16, 10.8.0.0/24")
    assert ip_allowed("192.168.1.5") and ip_allowed("10.8.0.9")
    assert not ip_allowed("10.9.0.1") and not ip_allowed("not-an-ip")


def test_lockout_grows_and_expires(settings):
    t0 = 1_000_000.0
    key = "ip:1.1.1.1"
    for i in range(sec.FREE_FAILURES - 1):
        sec.record_failure(key, t0 + i)
    assert sec.lockout_seconds(key, t0 + 5) == 0  # still within the free attempts
    sec.record_failure(key, t0 + 10)
    first = sec.lockout_seconds(key, t0 + 10)
    assert first > 0
    sec.record_failure(key, t0 + 11)
    assert sec.lockout_seconds(key, t0 + 11) > first  # delay increases
    assert sec.lockout_seconds(key, t0 + 11 + sec.WINDOW + 1) == 0  # failures age out


def test_lockout_is_per_key_and_clearable(settings):
    t0 = 2_000_000.0
    for i in range(sec.FREE_FAILURES):
        sec.record_failure("user:ab", t0 + i)
    assert sec.lockout_seconds("user:ab", t0 + 3) > 0
    assert sec.lockout_seconds("user:other", t0 + 3) == 0
    sec.clear_failures("user:ab")
    assert sec.lockout_seconds("user:ab", t0 + 3) == 0
