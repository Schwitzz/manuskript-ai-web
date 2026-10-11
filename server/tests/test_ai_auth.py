"""Every AI route must require a login: they can spend cloud credits and read project text."""

import pytest

from tests.conftest import csrf_headers

ROUTES = [
    ("get", "/api/ai/providers"),
    ("post", "/api/ai/providers"),
    ("get", "/api/ai/agents"),
    ("put", "/api/ai/agents"),
    ("get", "/api/ai/models"),
    ("post", "/api/ai/chats/new"),
    ("get", "/api/ai/chats"),
    ("get", "/api/ai/chats/abc"),
    ("delete", "/api/ai/chats/abc"),
    ("put", "/api/ai/chats/abc"),
    ("post", "/api/ai/chat"),
]


@pytest.mark.parametrize("method,path", ROUTES)
def test_ai_routes_reject_anonymous_requests(client, method, path):
    r = getattr(client, method)(path)
    # 401 (not logged in) or 403 (no CSRF token, checked first for writes); never a 2xx/422/500
    assert r.status_code in (401, 403), f"{method.upper()} {path} -> {r.status_code}"


def test_ai_chat_write_needs_csrf_token_when_logged_in(logged_in):
    body = {"project": "x", "messages": [{"role": "user", "content": "hi"}]}
    assert logged_in.post("/api/ai/chat", json=body).status_code == 403
    assert logged_in.post("/api/ai/chat", json=body, headers=csrf_headers(logged_in)).status_code == 200
