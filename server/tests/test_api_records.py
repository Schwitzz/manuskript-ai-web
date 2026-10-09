import shutil
from pathlib import Path

from msklib.project import Project
from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"
B = "/api/projects/acts"


def setup(client, tmp_path):
    shutil.copytree(FIX, tmp_path / "projects" / "acts")
    return csrf_headers(client)


def stable(tmp_path):
    return Project.load(tmp_path / "projects/acts").save() == []


def test_characters_crud(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    chars = logged_in.get(f"{B}/characters").json()["characters"]
    assert [c["name"] for c in chars][:2] == ["Peter", "Paul"]
    r = logged_in.post(f"{B}/characters", headers=h, json={
        "name": "Silas", "importance": "1", "color": "#112233", "motivation": "Follow Paul",
        "infos": [["Age", "40"]]})
    assert r.status_code == 201 and r.json()["id"] == 6
    u = logged_in.put(f"{B}/characters/6", headers=h, json={"name": "Silas the scribe",
                                                            "color": "#112233"})
    assert u.json()["name"] == "Silas the scribe"
    assert (tmp_path / "projects/acts/characters/6-Silas_the_scribe.txt").exists()
    assert not (tmp_path / "projects/acts/characters/6-Silas.txt").exists()
    assert logged_in.delete(f"{B}/characters/6", headers=h).status_code == 200
    assert logged_in.put(f"{B}/characters/6", headers=h, json={"name": "x"}).status_code == 404
    assert stable(tmp_path)


def test_character_validation(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    assert logged_in.post(f"{B}/characters", headers=h, json={"name": ""}).status_code == 422
    assert logged_in.post(f"{B}/characters", headers=h,
                          json={"name": "x", "color": "red"}).status_code == 422
    assert logged_in.post(f"{B}/characters", headers=h,
                          json={"name": "x", "importance": "9"}).status_code == 422


def test_deleting_a_character_unlinks_it_from_plots(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    assert logged_in.get(f"{B}/plots").json()["plots"][2]["characters"] == [1, 5]
    logged_in.delete(f"{B}/characters/5", headers=h)
    assert logged_in.get(f"{B}/plots").json()["plots"][2]["characters"] == [1]
    assert stable(tmp_path)


def test_labels_and_status(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    got = logged_in.get(f"{B}/labels").json()
    assert got["labels"][0] == {"name": "Idea", "color": "#ffff00"}
    logged_in.put(f"{B}/labels", headers=h, json={"labels": [{"name": "Draft", "color": "#abcdef"},
                                                             {"name": "Plain"}]})
    logged_in.put(f"{B}/status", headers=h, json={"status": ["Todo", "  ", "Done"]})
    again = logged_in.get(f"{B}/labels").json()
    assert again["labels"] == [{"name": "Draft", "color": "#abcdef"}, {"name": "Plain", "color": ""}]
    assert again["status"] == ["Todo", "Done"]
    assert logged_in.put(f"{B}/labels", headers=h, json={"labels": [
        {"name": "x" * 30}]}).status_code == 422
    assert stable(tmp_path)


def test_info_and_summary(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    logged_in.put(f"{B}/info", headers=h, json={"values": {"Title": "Acts", "Author": "Luke",
                                                          "Genre": ""}})
    logged_in.put(f"{B}/summary", headers=h, json={"values": {"Sentence": "One line"}})
    got = logged_in.get(f"{B}/info").json()
    assert got["info"] == {"Title": "Acts", "Author": "Luke"} and got["summary"] == {"Sentence": "One line"}
    assert stable(tmp_path)


def test_plots_crud_with_steps_and_links(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    r = logged_in.post(f"{B}/plots", headers=h, json={
        "name": "Mission", "importance": "2", "characters": [0, 1],
        "steps": [{"name": "Start", "summary": "Leave"}, {"name": "End", "summary": "Arrive"}]})
    assert r.status_code == 201
    pl = r.json()
    assert pl["id"] == 3 and [s["name"] for s in pl["steps"]] == ["Start", "End"]
    bad = logged_in.put(f"{B}/plots/3", headers=h, json={"name": "Mission", "characters": [77]})
    assert bad.status_code == 400
    logged_in.put(f"{B}/plots/3", headers=h, json={"name": "Mission 2", "characters": [1]})
    got = [x for x in logged_in.get(f"{B}/plots").json()["plots"] if x["id"] == 3][0]
    assert got["name"] == "Mission 2" and got["characters"] == [1] and got["steps"] == []
    assert logged_in.delete(f"{B}/plots/3", headers=h).status_code == 200
    assert len(logged_in.get(f"{B}/plots").json()["plots"]) == 3
    assert stable(tmp_path)


def test_world_tree(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    items = logged_in.get(f"{B}/world").json()["items"]
    assert [i["name"] for i in items] == ["Places", "Cultures", "Travel"]
    r = logged_in.post(f"{B}/world", headers=h, json={"name": "Antioch", "parent_id": 0,
                                                      "description": "A city"})
    new_id = r.json()["id"]
    assert new_id == 12
    logged_in.patch(f"{B}/world/{new_id}", headers=h, json={"passion": "Trade", "description": ""})
    places = logged_in.get(f"{B}/world").json()["items"][0]
    antioch = places["children"][-1]
    assert antioch["passion"] == "Trade" and antioch["description"] == ""
    assert logged_in.delete(f"{B}/world/{new_id}", headers=h).status_code == 200
    assert logged_in.delete(f"{B}/world/{new_id}", headers=h).status_code == 404
    assert stable(tmp_path)


def test_records_need_login_and_csrf(client, logged_in, tmp_path):
    setup(logged_in, tmp_path)
    assert logged_in.post(f"{B}/characters", json={"name": "x"}).status_code == 403
    logged_in.cookies.clear()
    for path in ("characters", "labels", "info", "plots", "world"):
        assert logged_in.get(f"{B}/{path}").status_code == 401
