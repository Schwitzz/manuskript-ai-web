import json
import os
import shutil
import time
from pathlib import Path

import pytest

from app import synclock
from msklib.project import Project
from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"


@pytest.fixture()
def proj(tmp_path):
    dest = tmp_path / "projects" / "acts"
    shutil.copytree(FIX, dest)
    return dest


def test_acquire_release_and_exclusion(proj):
    assert not synclock.is_locked(proj)
    assert synclock.acquire(proj) and synclock.is_locked(proj)
    assert synclock.acquire(proj) is False          # second taker is refused
    synclock.release(proj)
    assert not synclock.is_locked(proj) and not (proj / ".lock").exists()
    assert synclock.acquire(proj)


def test_marker_records_owner_and_time(proj):
    synclock.acquire(proj, owner="sync-pass")
    data = json.loads((proj / ".lock").read_text())
    assert data["owner"] == "sync-pass" and data["pid"] == os.getpid()
    assert abs(data["at"] - time.time()) < 5


def test_expired_marker_is_ignored_and_replaced(proj):
    (proj / ".lock").write_text(json.dumps({"owner": "crashed", "pid": 1, "at": time.time() - 3600}))
    assert not synclock.is_locked(proj)
    assert synclock.acquire(proj)
    assert json.loads((proj / ".lock").read_text())["owner"] == "sync"


def test_garbage_marker_never_locks_a_project_forever(proj):
    for junk in ("", "not json", "{}", '{"at": "x"}', "[1]"):
        (proj / ".lock").write_text(junk)
        assert not synclock.is_locked(proj), junk


def test_refresh_keeps_a_long_pass_alive(proj):
    synclock.acquire(proj)
    old = json.loads((proj / ".lock").read_text())
    (proj / ".lock").write_text(json.dumps({**old, "at": time.time() - synclock.MAX_AGE + 5}))
    time.sleep(0.01)
    synclock.refresh(proj)
    assert json.loads((proj / ".lock").read_text())["at"] > time.time() - 5


def test_held_context_releases_even_on_error(proj):
    with pytest.raises(ValueError):
        with synclock.held(proj):
            assert synclock.is_locked(proj)
            raise ValueError
    assert not synclock.is_locked(proj)
    synclock.acquire(proj)
    with pytest.raises(RuntimeError):
        with synclock.held(proj):
            pass
    assert synclock.is_locked(proj)  # the failed attempt must not release the other holder's lock


def test_the_marker_is_invisible_to_msklib_and_the_desktop_format(proj):
    synclock.acquire(proj)
    assert Project.load(proj).save() == []
    from app import events
    before = events.signature(proj)
    synclock.release(proj)
    assert events.signature(proj) == before          # not counted as a project change


def test_writes_get_423_while_locked_but_reads_work(logged_in, tmp_path, proj):
    h = csrf_headers(logged_in)
    doc = logged_in.get("/api/projects/acts/documents/12").json()
    synclock.acquire(proj)
    assert logged_in.get("/api/projects/acts/documents/12").status_code == 200
    assert logged_in.get("/api/projects/acts/outline").status_code == 200
    assert logged_in.get("/api/projects/acts/search", params={"q": "lame"}).status_code == 200
    writes = [
        ("put", "/api/projects/acts/documents/12", {"text": "x", "base_version": doc["version"]}),
        ("patch", "/api/projects/acts/outline/12/title", {"title": "New"}),
        ("post", "/api/projects/acts/outline", {"title": "s"}),
        ("delete", "/api/projects/acts/outline/12", None),
        ("post", "/api/projects/acts/characters", {"name": "x"}),
        ("put", "/api/projects/acts/status", {"status": ["a"]}),
        ("post", "/api/projects/acts/plots", {"name": "p"}),
        ("post", "/api/projects/acts/world", {"name": "w"}),
        ("patch", "/api/projects/acts/settings", {"countSpaces": False}),
    ]
    for method, url, body in writes:
        r = getattr(logged_in, method)(url, headers=h, **({"json": body} if body is not None else {}))
        assert r.status_code == 423, (method, url, r.status_code)
    assert logged_in.get("/api/projects/acts/documents/12").json()["text"] == doc["text"]
    synclock.release(proj)
    ok = logged_in.put("/api/projects/acts/documents/12", headers=h,
                       json={"text": "now ok", "base_version": doc["version"]})
    assert ok.status_code == 200
