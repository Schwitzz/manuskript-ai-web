import shutil
import threading
from pathlib import Path

from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"


def install_sample(client, tmp_path, name="acts"):
    shutil.copytree(FIX, tmp_path / "projects" / name)


def test_requires_login(client):
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/projects/acts/outline").status_code == 401


def test_list_and_outline(logged_in, tmp_path):
    install_sample(logged_in, tmp_path)
    assert logged_in.get("/api/projects").json() == {
        "projects": [{"name": "acts", "title": "The Acts of the Apostles"}]}
    o = logged_in.get("/api/projects/acts/outline").json()
    assert [i["title"] for i in o["items"]] == ["Jerusalem", "Judea and Samaria",
                                               "To the extremities of the world"]
    assert o["words"] > 1000


def test_create_project(logged_in):
    h = csrf_headers(logged_in)
    r = logged_in.post("/api/projects", json={"name": "Novel", "title": "My Novel"}, headers=h)
    assert r.status_code == 201
    assert logged_in.post("/api/projects", json={"name": "Novel"}, headers=h).status_code == 409
    assert logged_in.get("/api/projects").json()["projects"][0]["title"] == "My Novel"


def test_bad_names_are_rejected(logged_in):
    h = csrf_headers(logged_in)
    for bad in ["../evil", "a/b", ".hidden", "..", "x\\y"]:
        r = logged_in.post("/api/projects", json={"name": bad}, headers=h)
        assert r.status_code in (400, 422), bad
    assert logged_in.get("/api/projects/..%2F..%2Fetc/outline").status_code in (400, 404)
    assert logged_in.get("/api/projects/nope/outline").status_code == 404


def test_read_and_save_document(logged_in, tmp_path):
    install_sample(logged_in, tmp_path)
    h = csrf_headers(logged_in)
    doc = logged_in.get("/api/projects/acts/documents/12").json()
    assert doc["title"] == "Peter preaches" and doc["text"].startswith("11 As the lame man")
    r = logged_in.put("/api/projects/acts/documents/12", headers=h,
                      json={"text": doc["text"] + "\nNew line", "base_version": doc["version"]})
    assert r.status_code == 200 and r.json()["version"] != doc["version"]
    again = logged_in.get("/api/projects/acts/documents/12").json()
    assert again["text"].endswith("New line") and again["version"] == r.json()["version"]
    on_disk = next((tmp_path / "projects/acts/outline").rglob("1-Peter_preaches.md")).read_text()
    assert on_disk.endswith("New line")


def test_stale_save_is_rejected_and_nothing_is_overwritten(logged_in, tmp_path):
    install_sample(logged_in, tmp_path)
    h = csrf_headers(logged_in)
    first = logged_in.get("/api/projects/acts/documents/12").json()
    logged_in.put("/api/projects/acts/documents/12", headers=h,
                  json={"text": "phone edit", "base_version": first["version"]})
    stale = logged_in.put("/api/projects/acts/documents/12", headers=h,
                          json={"text": "laptop edit", "base_version": first["version"]})
    assert stale.status_code == 409
    assert stale.json()["detail"]["text"] == "phone edit"
    assert logged_in.get("/api/projects/acts/documents/12").json()["text"] == "phone edit"


def test_edit_made_outside_the_app_is_noticed(logged_in, tmp_path):
    install_sample(logged_in, tmp_path)
    h = csrf_headers(logged_in)
    doc = logged_in.get("/api/projects/acts/documents/12").json()
    f = next((tmp_path / "projects/acts/outline").rglob("1-Peter_preaches.md"))
    f.write_text(f.read_text() + "\nedited on the desktop")
    r = logged_in.put("/api/projects/acts/documents/12", headers=h,
                      json={"text": "mine", "base_version": doc["version"]})
    assert r.status_code == 409 and "edited on the desktop" in r.json()["detail"]["text"]


def test_folder_and_missing_document_404(logged_in, tmp_path):
    install_sample(logged_in, tmp_path)
    assert logged_in.get("/api/projects/acts/documents/35").status_code == 404  # a folder
    assert logged_in.get("/api/projects/acts/documents/9999").status_code == 404


def test_save_needs_csrf(logged_in, tmp_path):
    install_sample(logged_in, tmp_path)
    r = logged_in.put("/api/projects/acts/documents/12", json={"text": "x", "base_version": "y"})
    assert r.status_code == 403


def test_two_simultaneous_saves_exactly_one_wins(logged_in, tmp_path):
    install_sample(logged_in, tmp_path)
    h = csrf_headers(logged_in)
    version = logged_in.get("/api/projects/acts/documents/12").json()["version"]
    results = []

    def save(text):
        results.append(logged_in.put("/api/projects/acts/documents/12", headers=h,
                                     json={"text": text, "base_version": version}).status_code)

    threads = [threading.Thread(target=save, args=(f"writer {i}",)) for i in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == [200] + [409] * 5
    final = logged_in.get("/api/projects/acts/documents/12").json()["text"]
    assert final.startswith("writer ")
