"""Every API route must reject an anonymous caller, except the few that are public on purpose.

This walks the real route table, so a new router that forgets `Depends(current_user)` fails
here instead of shipping open (the AI router did, once).
"""

import re

import pytest

from app.main import create_app

# Public by design: health check, login flow, and first-run setup (which refuses once a user exists).
PUBLIC = {
    ("GET", "/api/health"),
    ("GET", "/api/auth/status"),
    ("POST", "/api/auth/setup"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/totp/verify"),  # needs the half-logged-in (password OK) session instead
    ("POST", "/api/auth/logout"),       # only clears cookies; CSRF-checked
}


def _all() -> set[tuple[str, str]]:
    """Every (METHOD, path) the app serves. Read from the OpenAPI schema because the routers
    are nested, so `app.routes` alone does not list them."""
    paths = create_app().openapi()["paths"]
    return {(m.upper(), p) for p, ops in paths.items() if p.startswith("/api/")
            for m in ops if m in ("get", "post", "put", "patch", "delete")}


def _routes():
    for method, path in sorted(_all() - PUBLIC):
        yield pytest.param(method, path, id=f"{method} {path}")


@pytest.mark.parametrize("method,path", list(_routes()))
def test_route_rejects_anonymous_callers(client, method, path):
    url = re.sub(r"\{[^}]+\}", "1", path)
    r = client.request(method, url)
    # 401 = not logged in; 403 = CSRF check (it runs first on writes). Never a 2xx, 404, 422 or 500.
    assert r.status_code in (401, 403), f"{method} {path} answered {r.status_code} to an anonymous caller"


def test_the_public_list_matches_reality():
    """Catches a stale allowlist: every entry must still be a real route."""
    assert PUBLIC <= _all()


def test_there_are_routes_to_check():
    assert len(list(_routes())) > 40  # guards against the walk silently finding nothing
