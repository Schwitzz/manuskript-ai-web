import pytest
from fastapi.testclient import TestClient

from app.config import get_settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MSK_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MSK_SECRET_KEY", "test-secret")
    monkeypatch.setenv("MSK_COOKIE_SECURE", "false")
    get_settings.cache_clear()
    from app.main import create_app
    with TestClient(create_app()) as c:
        yield c
    get_settings.cache_clear()


def csrf_headers(c: TestClient) -> dict:
    return {"x-csrf-token": c.cookies.get("msk_csrf", "")}


@pytest.fixture()
def logged_in(client):
    r = client.post("/api/auth/setup", json={"username": "ab", "password": "correct horse battery"})
    assert r.status_code == 200
    return client
