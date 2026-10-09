import shutil
from pathlib import Path

from msklib import references as R
from msklib.project import Project
from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"
B = "/api/projects/acts/references"


def setup(client, tmp_path):
    shutil.copytree(FIX, tmp_path / "projects" / "acts")
    return csrf_headers(client)


def test_find_and_make():
    text = "see {C:3:Stephen} and {P:2:Fight}, {T:12:} not {X:1:y} or {C:x:y}"
    assert R.find(text) == [("character", 3), ("plot", 2), ("scene", 12)]
    assert R.make("world", 5, "Rome") == "{W:5:Rome}"
    assert R.find(R.make("scene", 9, "A title: with colon")) == [("scene", 9)]
    assert R.find("") == [] and R.find(None) == []


def test_backlinks_in_the_real_sample():
    p = Project.load(FIX)
    links = R.backlinks(p, "plot", 2)
    assert sorted(x["id"] for x in links) == [38, 44, 51, 59]
    assert all(x["field"] == "notes" and x["kind"] == "scene" for x in links)
    assert R.backlinks(p, "scene", 12) == []


def test_api_backlinks_and_titles(logged_in, tmp_path):
    setup(logged_in, tmp_path)
    r = logged_in.get(f"{B}/plot/2").json()
    assert r["target_title"] == "Paul and Barnabas fight" and len(r["backlinks"]) == 4
    assert logged_in.get(f"{B}/character/5").json()["target_title"] == "Barnabas"
    assert logged_in.get(f"{B}/world/1").json()["target_title"] == "Jerusalem"
    assert logged_in.get(f"{B}/scene/12").json()["target_title"] == "Peter preaches"
    assert logged_in.get(f"{B}/scene/9999").status_code == 404
    assert logged_in.get(f"{B}/nonsense/1").status_code == 422


def test_a_new_reference_shows_up_and_deleting_the_target_breaks_it(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    assert logged_in.get(f"{B}/broken").json() == {"broken": []}
    logged_in.patch("/api/projects/acts/outline/12/fields", headers=h,
                    json={"notes": "Meets {C:4:Herod} and {W:5:Rome}"})
    before_rome = {b["id"] for b in R.backlinks(Project.load(FIX), "world", 5)}
    assert 12 not in before_rome
    assert [b["id"] for b in logged_in.get(f"{B}/character/4").json()["backlinks"]] == [12]
    after_rome = {b["id"] for b in logged_in.get(f"{B}/world/5").json()["backlinks"]}
    assert after_rome == before_rome | {12}
    logged_in.delete("/api/projects/acts/characters/4", headers=h)
    broken = logged_in.get(f"{B}/broken").json()["broken"]
    assert broken == [{"source_kind": "scene", "source_id": 12, "source_title": "Peter preaches",
                       "field": "notes", "target_kind": "character", "target_id": 4}]
    assert logged_in.get(f"{B}/character/4").status_code == 404


def test_references_in_scene_text_and_nothing_is_modified_by_reading(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    doc = logged_in.get("/api/projects/acts/documents/12").json()
    logged_in.put("/api/projects/acts/documents/12", headers=h,
                  json={"text": doc["text"] + "\nSee {T:13:Peter heals a beggar}.",
                        "base_version": doc["version"]})
    assert [b["field"] for b in logged_in.get(f"{B}/scene/13").json()["backlinks"]] == ["text"]
    before = {p: p.read_bytes() for p in (tmp_path / "projects/acts").rglob("*") if p.is_file()}
    logged_in.get(f"{B}/broken")
    logged_in.get(f"{B}/scene/13")
    assert before == {p: p.read_bytes() for p in (tmp_path / "projects/acts").rglob("*") if p.is_file()}


def test_auth(logged_in, tmp_path):
    setup(logged_in, tmp_path)
    logged_in.cookies.clear()
    assert logged_in.get(f"{B}/broken").status_code == 401
