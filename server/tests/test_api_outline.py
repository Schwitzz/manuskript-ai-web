import shutil
from pathlib import Path

from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"
BASE = "/api/projects/acts/outline"


def setup(client, tmp_path):
    shutil.copytree(FIX, tmp_path / "projects" / "acts")
    return csrf_headers(client)


def tree(client):
    return client.get(BASE).json()["items"]


def flat(items):
    for i in items:
        yield i
        yield from flat(i["children"])


def by_title(client, title):
    return next(i for i in flat(tree(client)) if i["title"] == title)


def test_create_scene_and_folder(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    ch3 = by_title(logged_in, "Chapter 3")
    r = logged_in.post(BASE, headers=h, json={"title": "New scene", "parent_id": ch3["id"], "position": 0})
    assert r.status_code == 201 and r.json()["type"] == "md"
    new = by_title(logged_in, "Chapter 3")["children"]
    assert [c["title"] for c in new][:2] == ["New scene", "Peter heals a beggar"]
    f = logged_in.post(BASE, headers=h, json={"title": "Part 4", "type": "folder"})
    assert f.status_code == 201 and tree(logged_in)[-1]["title"] == "Part 4"
    # ids are unique
    ids = [i["id"] for i in flat(tree(logged_in))]
    assert len(ids) == len(set(ids))


def test_cannot_create_inside_a_scene(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    scene = by_title(logged_in, "Peter preaches")
    r = logged_in.post(BASE, headers=h, json={"title": "x", "parent_id": scene["id"]})
    assert r.status_code == 400


def test_rename(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    scene = by_title(logged_in, "Peter preaches")
    r = logged_in.patch(f"{BASE}/{scene['id']}/title", headers=h, json={"title": "Peter speaks"})
    assert r.status_code == 200
    assert by_title(logged_in, "Peter speaks")["id"] == scene["id"]
    doc = logged_in.get(f"/api/projects/acts/documents/{scene['id']}").json()
    assert doc["text"].startswith("11 As the lame man")  # content survived the file rename


def test_move_between_folders_and_reorder(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    scene = by_title(logged_in, "Peter preaches")
    ch4 = by_title(logged_in, "Chapter 4")
    r = logged_in.post(f"{BASE}/{scene['id']}/move", headers=h,
                       json={"parent_id": ch4["id"], "position": 0})
    assert r.status_code == 200
    kids = by_title(logged_in, "Chapter 4")["children"]
    assert kids[0]["id"] == scene["id"] and len(kids) == 4
    assert len(by_title(logged_in, "Chapter 3")["children"]) == 1
    assert logged_in.get(f"/api/projects/acts/documents/{scene['id']}").json()["text"]


def test_cannot_move_folder_into_itself(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    top = tree(logged_in)[0]
    inner = top["children"][0]
    for target in (top["id"], inner["id"]):
        r = logged_in.post(f"{BASE}/{top['id']}/move", headers=h,
                           json={"parent_id": target, "position": 0})
        assert r.status_code == 400
    assert tree(logged_in)[0]["id"] == top["id"]


def test_set_and_clear_fields(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    scene = by_title(logged_in, "Peter preaches")
    url = f"{BASE}/{scene['id']}/fields"
    r = logged_in.patch(url, headers=h, json={"label": "2", "status": "1", "pov": "1",
                                              "summary_sentence": "Peter speaks to a crowd",
                                              "goal": "500", "compile": "0"})
    meta = r.json()["meta"]
    assert meta["label"] == "2" and meta["POV"] == "1" and meta["setGoal"] == "500"
    assert meta["summarySentence"] == "Peter speaks to a crowd" and meta["compile"] == "0"
    cleared = logged_in.patch(url, headers=h, json={"label": ""}).json()["meta"]
    assert "label" not in cleared and cleared["status"] == "1"  # untouched fields stay


def test_delete_goes_to_trash(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    scene = by_title(logged_in, "Peter preaches")
    assert logged_in.delete(f"{BASE}/{scene['id']}", headers=h).status_code == 200
    assert logged_in.get(f"/api/projects/acts/documents/{scene['id']}").status_code == 404
    assert list((tmp_path / "projects/acts/.trash").rglob("*Peter_preaches*"))


def test_delete_folder_trashes_children_too(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    ch2 = by_title(logged_in, "Chapter 2")
    assert logged_in.delete(f"{BASE}/{ch2['id']}", headers=h).status_code == 200
    trashed = list((tmp_path / "projects/acts/.trash").rglob("*.md"))
    assert len(trashed) == 3


def test_unknown_item_and_csrf(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    assert logged_in.delete(f"{BASE}/9999", headers=h).status_code == 404
    assert logged_in.delete(f"{BASE}/12").status_code == 403
    bad = logged_in.post(BASE, headers=h, json={"title": "x", "type": "weird"})
    assert bad.status_code == 422


def test_desktop_compatible_after_api_edits(logged_in, tmp_path):
    """After a series of API edits the folder still round-trips untouched."""
    from msklib.project import Project
    h = setup(logged_in, tmp_path)
    scene = by_title(logged_in, "Peter preaches")
    logged_in.patch(f"{BASE}/{scene['id']}/title", headers=h, json={"title": "Renamed"})
    logged_in.post(BASE, headers=h, json={"title": "Added: colon"})
    logged_in.delete(f"{BASE}/{by_title(logged_in, 'Chapter 5')['id']}", headers=h)
    assert Project.load(tmp_path / "projects/acts").save() == []
