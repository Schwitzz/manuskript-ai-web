from msklib.project import Project
from tests.conftest import csrf_headers


def test_lists_bundled_samples(logged_in):
    assert logged_in.get("/api/projects/samples").json() == {"samples": ["book-of-acts"]}


def test_create_from_sample_is_a_complete_editable_copy(logged_in, tmp_path):
    h = csrf_headers(logged_in)
    r = logged_in.post("/api/projects", headers=h, json={"name": "Try", "sample": "book-of-acts"})
    assert r.status_code == 201
    assert (tmp_path / "projects/Try.msk").read_text() == "1"
    assert Project.load(tmp_path / "projects/Try").save() == []
    o = logged_in.get("/api/projects/Try/outline").json()
    assert o["title"] == "The Acts of the Apostles" and o["words"] > 1000
    doc = logged_in.get("/api/projects/Try/documents/12").json()
    ok = logged_in.put("/api/projects/Try/documents/12", headers=h,
                       json={"text": "mine", "base_version": doc["version"]})
    assert ok.status_code == 200


def test_samples_are_copies_never_shared(logged_in, tmp_path):
    h = csrf_headers(logged_in)
    logged_in.post("/api/projects", headers=h, json={"name": "A", "sample": "book-of-acts"})
    doc = logged_in.get("/api/projects/A/documents/12").json()
    logged_in.put("/api/projects/A/documents/12", headers=h,
                  json={"text": "changed", "base_version": doc["version"]})
    logged_in.post("/api/projects", headers=h, json={"name": "B", "sample": "book-of-acts"})
    assert logged_in.get("/api/projects/B/documents/12").json()["text"].startswith("11 As the lame")
    from app.projects import SAMPLES_DIR
    scene = next((SAMPLES_DIR / "book-of-acts/outline").rglob("1-Peter_preaches.md"))
    assert "changed" not in scene.read_text()


def test_sample_errors(logged_in):
    h = csrf_headers(logged_in)
    assert logged_in.post("/api/projects", headers=h,
                          json={"name": "X", "sample": "../../etc"}).status_code == 404
    assert logged_in.post("/api/projects", headers=h,
                          json={"name": "X", "sample": "nope"}).status_code == 404
    assert logged_in.post("/api/projects", headers=h,
                          json={"name": "Y", "sample": "book-of-acts"}).status_code == 201
    assert logged_in.post("/api/projects", headers=h,
                          json={"name": "Y", "sample": "book-of-acts"}).status_code == 409
    assert logged_in.post("/api/projects", headers=h,
                          json={"name": "../bad", "sample": "book-of-acts"}).status_code in (400, 422)
