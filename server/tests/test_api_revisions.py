import shutil
from pathlib import Path

from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"
DOC = "/api/projects/acts/documents/12"
HIST = "/api/projects/acts/documents/1"  # "Introduction": has two revisions in the sample


def setup(client, tmp_path):
    shutil.copytree(FIX, tmp_path / "projects" / "acts")
    return csrf_headers(client)


def test_list_existing_revisions(logged_in, tmp_path):
    setup(logged_in, tmp_path)
    assert logged_in.get(f"{DOC}/revisions").json() == {"revisions": []}  # none recorded yet
    revs = logged_in.get(f"{HIST}/revisions").json()["revisions"]
    assert len(revs) == 2 and revs == sorted(revs, key=lambda r: -r["timestamp"])
    assert all(r["words"] > 0 for r in revs)
    one = logged_in.get(f"{HIST}/revisions/{revs[0]['timestamp']}").json()
    assert one["text"] and one["timestamp"] == revs[0]["timestamp"]


def test_saving_adds_a_revision_with_the_old_text(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    doc = logged_in.get(DOC).json()
    before = len(logged_in.get(f"{DOC}/revisions").json()["revisions"])
    logged_in.put(DOC, headers=h, json={"text": "rewritten", "base_version": doc["version"]})
    revs = logged_in.get(f"{DOC}/revisions").json()["revisions"]
    assert len(revs) == before + 1
    newest = logged_in.get(f"{DOC}/revisions/{revs[0]['timestamp']}").json()
    assert newest["text"] == doc["text"]


def test_restore_brings_back_old_text_and_keeps_current_as_revision(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    doc = logged_in.get(DOC).json()
    logged_in.put(DOC, headers=h, json={"text": "v2", "base_version": doc["version"]})
    cur = logged_in.get(DOC).json()
    ts = logged_in.get(f"{DOC}/revisions").json()["revisions"][0]["timestamp"]
    r = logged_in.post(f"{DOC}/revisions/{ts}/restore", headers=h, json={"base_version": cur["version"]})
    assert r.status_code == 200 and r.json()["text"] == doc["text"]
    assert logged_in.get(DOC).json()["text"] == doc["text"]


def test_restore_with_stale_version_is_rejected(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    ts = logged_in.get(f"{HIST}/revisions").json()["revisions"][0]["timestamp"]
    r = logged_in.post(f"{HIST}/revisions/{ts}/restore", headers=h, json={"base_version": "stale"})
    assert r.status_code == 409


def test_unknown_revision_folder_and_auth(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    assert logged_in.get(f"{DOC}/revisions/1").status_code == 404
    assert logged_in.get("/api/projects/acts/documents/35/revisions").status_code == 404
    assert logged_in.post(f"{DOC}/revisions/1/restore", json={"base_version": "x"}).status_code == 403
    logged_in.cookies.clear()
    assert logged_in.get(f"{DOC}/revisions").status_code == 401
