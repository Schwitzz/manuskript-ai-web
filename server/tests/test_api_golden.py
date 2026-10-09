"""Golden tests through the API: using the app must never change a byte it was not asked to."""

import shutil
from pathlib import Path

import pytest

from tests.conftest import csrf_headers

FIXTURES = Path(__file__).parent / "fixtures"
PROJECTS = ["book-of-acts", "draft-0001"]


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def install(tmp_path, name) -> Path:
    dest = tmp_path / "projects" / name
    shutil.copytree(FIXTURES / name, dest)
    return dest


def scenes(items):
    for i in items:
        if i["type"] != "folder":
            yield i
        yield from scenes(i["children"])


@pytest.mark.parametrize("name", PROJECTS)
def test_reading_everything_through_the_api_changes_nothing(logged_in, tmp_path, name):
    root = install(tmp_path, name)
    before = snapshot(root)
    base = f"/api/projects/{name}"
    assert logged_in.get("/api/projects").status_code == 200
    outline = logged_in.get(f"{base}/outline").json()
    for s in scenes(outline["items"]):
        assert logged_in.get(f"{base}/documents/{s['id']}").status_code == 200
        assert logged_in.get(f"{base}/documents/{s['id']}/revisions").status_code == 200
    for path in ("characters", "labels", "info", "plots", "world", "settings"):
        assert logged_in.get(f"{base}/{path}").status_code == 200, path
    assert logged_in.get(f"{base}/search", params={"q": "the"}).status_code == 200
    assert logged_in.get(f"{base}/download").status_code == 200
    assert snapshot(root) == before


@pytest.mark.parametrize("name", PROJECTS)
def test_saving_every_scene_unchanged_through_the_api_changes_nothing(logged_in, tmp_path, name):
    root = install(tmp_path, name)
    before = snapshot(root)
    h = csrf_headers(logged_in)
    base = f"/api/projects/{name}"
    for s in scenes(logged_in.get(f"{base}/outline").json()["items"]):
        doc = logged_in.get(f"{base}/documents/{s['id']}").json()
        r = logged_in.put(f"{base}/documents/{s['id']}", headers=h,
                          json={"text": doc["text"], "base_version": doc["version"]})
        assert r.status_code == 200 and r.json()["version"] == doc["version"]
    assert snapshot(root) == before


@pytest.mark.parametrize("name", PROJECTS)
def test_writing_every_record_back_unchanged_changes_nothing(logged_in, tmp_path, name):
    """Echo each record back exactly as the API gave it: a form that was opened and saved
    without edits must not rewrite the project."""
    root = install(tmp_path, name)
    before = snapshot(root)
    h = csrf_headers(logged_in)
    base = f"/api/projects/{name}"

    for c in logged_in.get(f"{base}/characters").json()["characters"]:
        body = {k: v for k, v in c.items() if k != "id"}
        assert logged_in.put(f"{base}/characters/{c['id']}", headers=h, json=body).status_code == 200
    labels = logged_in.get(f"{base}/labels").json()
    assert logged_in.put(f"{base}/labels", headers=h, json={"labels": labels["labels"]}).status_code == 200
    assert logged_in.put(f"{base}/status", headers=h, json={"status": labels["status"]}).status_code == 200
    info = logged_in.get(f"{base}/info").json()
    assert logged_in.put(f"{base}/info", headers=h, json={"values": info["info"]}).status_code == 200
    assert logged_in.put(f"{base}/summary", headers=h, json={"values": info["summary"]}).status_code == 200
    for pl in logged_in.get(f"{base}/plots").json()["plots"]:
        body = {k: v for k, v in pl.items() if k not in ("id",)}
        body["steps"] = [{k: v for k, v in s.items() if k != "id"} for s in pl["steps"]]
        assert logged_in.put(f"{base}/plots/{pl['id']}", headers=h, json=body).status_code == 200
    s = logged_in.get(f"{base}/settings").json()
    assert logged_in.patch(f"{base}/settings", headers=h,
                           json={"countSpaces": s["countSpaces"], "viewMode": s["viewMode"]}).status_code == 200
    changed = sorted(k for k in set(snapshot(root)) | set(before) if snapshot(root).get(k) != before.get(k))
    assert changed == [], changed
