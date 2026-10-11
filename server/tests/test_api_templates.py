from msklib.project import Project
from tests.conftest import csrf_headers


def make_acts(client, h, name="Acts"):
    assert client.post("/api/projects", headers=h,
                       json={"name": name, "sample": "book-of-acts"}).status_code == 201


def test_requires_login(client):
    assert client.get("/api/templates").status_code == 401


def test_empty_list(logged_in):
    assert logged_in.get("/api/templates").json() == {"templates": []}


def test_structure_only_template_empties_scenes(logged_in, tmp_path):
    h = csrf_headers(logged_in)
    make_acts(logged_in, h)
    r = logged_in.post("/api/templates", headers=h, json={"name": "Three-act", "from_project": "Acts"})
    assert r.status_code == 201
    assert logged_in.get("/api/templates").json() == {"templates": ["Three-act"]}
    tpl = Project.load(tmp_path / "templates/Three-act")
    scenes = [i for i in tpl.outline.walk() if not i.is_folder]
    assert scenes and all(i.text == "" for i in scenes)
    # the structure (titles, nesting) survives, the revision history does not
    assert [c.title for c in tpl.outline.children] == ["Jerusalem", "Judea and Samaria",
                                                         "To the extremities of the world"]
    assert not (tmp_path / "templates/Three-act/revisions.xml").exists()
    # the source project is untouched
    assert logged_in.get("/api/projects/Acts/outline").json()["words"] > 1000


def test_template_can_keep_text(logged_in, tmp_path):
    h = csrf_headers(logged_in)
    make_acts(logged_in, h)
    logged_in.post("/api/templates", headers=h,
                   json={"name": "Full", "from_project": "Acts", "keep_text": True})
    tpl = Project.load(tmp_path / "templates/Full")
    assert sum(len(i.text) for i in tpl.outline.walk()) > 1000


def test_new_project_from_template_is_an_independent_copy(logged_in, tmp_path):
    h = csrf_headers(logged_in)
    make_acts(logged_in, h)
    logged_in.post("/api/templates", headers=h, json={"name": "T", "from_project": "Acts"})
    r = logged_in.post("/api/projects", headers=h,
                       json={"name": "Mine", "title": "My Book", "template": "T"})
    assert r.status_code == 201
    assert (tmp_path / "projects/Mine.msk").read_text() == "1"
    assert logged_in.get("/api/projects/Mine/outline").json()["title"] == "My Book"
    assert logged_in.get("/api/projects/Mine/outline").json()["words"] == 0
    # editing the new project never touches the template, and a second copy starts clean
    outline = logged_in.get("/api/projects/Mine/outline").json()
    first = outline["items"][0]["children"][0]["children"][0]["id"]
    doc = logged_in.get(f"/api/projects/Mine/documents/{first}").json()
    assert logged_in.put(f"/api/projects/Mine/documents/{first}", headers=h,
                         json={"text": "changed", "base_version": doc["version"]}).status_code == 200
    logged_in.post("/api/projects", headers=h, json={"name": "Other", "template": "T"})
    assert logged_in.get(f"/api/projects/Other/documents/{first}").json()["text"] == ""
    assert all(i.text == "" for i in Project.load(tmp_path / "templates/T").outline.walk()
               if not i.is_folder)


def test_title_defaults_to_project_name(logged_in):
    h = csrf_headers(logged_in)
    make_acts(logged_in, h)
    logged_in.post("/api/templates", headers=h, json={"name": "T", "from_project": "Acts"})
    logged_in.post("/api/projects", headers=h, json={"name": "Untitled", "template": "T"})
    assert logged_in.get("/api/projects/Untitled/outline").json()["title"] == "Untitled"


def test_errors(logged_in):
    h = csrf_headers(logged_in)
    make_acts(logged_in, h)
    assert logged_in.post("/api/templates", headers=h,
                          json={"name": "T", "from_project": "Nope"}).status_code == 404
    assert logged_in.post("/api/templates", headers=h,
                          json={"name": "T", "from_project": "Acts"}).status_code == 201
    assert logged_in.post("/api/templates", headers=h,
                          json={"name": "T", "from_project": "Acts"}).status_code == 409
    for bad in ("../evil", "a/b", ".hidden", ".."):
        assert logged_in.post("/api/templates", headers=h,
                              json={"name": bad, "from_project": "Acts"}).status_code in (400, 422)
        assert logged_in.post("/api/projects", headers=h,
                              json={"name": "X", "template": bad}).status_code in (400, 404, 422)
    assert logged_in.post("/api/projects", headers=h,
                          json={"name": "X", "template": "missing"}).status_code == 404
    assert logged_in.post("/api/projects", headers=h,
                          json={"name": "Acts", "template": "T"}).status_code == 409
    assert logged_in.post("/api/projects", headers=h,
                          json={"name": "X", "template": "T", "sample": "book-of-acts"}).status_code == 400
    # failed attempts must not leave half-made projects behind
    names = [p["name"] for p in logged_in.get("/api/projects").json()["projects"]]
    assert names == ["Acts"]


def test_delete_goes_to_trash(logged_in, tmp_path):
    h = csrf_headers(logged_in)
    make_acts(logged_in, h)
    logged_in.post("/api/templates", headers=h, json={"name": "T", "from_project": "Acts"})
    r = logged_in.delete("/api/templates/T", headers=h)
    assert r.status_code == 200
    assert logged_in.get("/api/templates").json() == {"templates": []}
    assert (tmp_path / "templates/.trash" / r.json()["trashed_as"] / "MANUSKRIPT").exists()
    assert logged_in.delete("/api/templates/T", headers=h).status_code == 404
