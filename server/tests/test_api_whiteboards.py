import json
import shutil
from pathlib import Path

from msklib.project import Project
from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"
URL = "/api/projects/acts/whiteboards"


def setup(client, tmp_path):
    shutil.copytree(FIX, tmp_path / "projects" / "acts")
    return csrf_headers(client)


def test_get_whiteboards_returns_default_when_missing(logged_in, tmp_path):
    setup(logged_in, tmp_path)
    res = logged_in.get(URL)
    assert res.status_code == 200
    data = res.json()
    assert data["active_board_id"] == "default"
    assert len(data["boards"]) == 1
    assert data["boards"][0]["id"] == "default"
    assert data["boards"][0]["name"] == "Main Board"
    assert data["boards"][0]["nodes"] == []
    assert data["boards"][0]["edges"] == []


def test_put_and_get_multiple_whiteboards_with_colors(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    payload = {
        "active_board_id": "board_2",
        "boards": [
            {
                "id": "default",
                "name": "Main Board",
                "nodes": [
                    {
                        "id": "n1",
                        "type": "shape",
                        "position": {"x": 100, "y": 150},
                        "data": {"shape": "rectangle", "label": "Hero", "note": "Brave", "color": "#ef4444"},
                    }
                ],
                "edges": [
                    {
                        "id": "e1",
                        "source": "n1",
                        "target": "n2",
                        "type": "dashed",
                        "data": {"lineType": "dash", "color": "#22c55e"},
                    }
                ],
                "viewport": {"x": 10.0, "y": 20.0, "zoom": 1.25},
                "show_all_notes": True,
            },
            {
                "id": "board_2",
                "name": "Subplot Map",
                "nodes": [
                    {
                        "id": "n2",
                        "type": "note",
                        "position": {"x": 50, "y": 60},
                        "data": {"text": "Plot twist", "color": "#eab308"},
                    }
                ],
                "edges": [],
                "viewport": {"x": 0.0, "y": 0.0, "zoom": 1.0},
                "show_all_notes": False,
            },
        ],
    }
    put_res = logged_in.put(URL, headers=h, json=payload)
    assert put_res.status_code == 200
    assert put_res.json() == payload

    # Verify file on disk in the project folder
    wb_file = tmp_path / "projects" / "acts" / "whiteboards.json"
    assert wb_file.exists()
    on_disk = json.loads(wb_file.read_text())
    assert on_disk["active_board_id"] == "board_2"
    assert len(on_disk["boards"]) == 2
    assert on_disk["boards"][0]["nodes"][0]["data"]["color"] == "#ef4444"
    assert on_disk["boards"][0]["edges"][0]["data"]["color"] == "#22c55e"

    # Verify GET reads it back identically
    get_res = logged_in.get(URL)
    assert get_res.status_code == 200
    assert get_res.json() == payload

    # Verify msklib round-trip does not delete or corrupt whiteboards.json
    proj = Project.load(tmp_path / "projects" / "acts")
    proj.infos["Title"] = "Updated Acts"
    proj.save()
    assert wb_file.exists()
    assert json.loads(wb_file.read_text()) == on_disk


def test_duplicate_board_ids_rejected(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    bad = {
        "active_board_id": "b1",
        "boards": [
            {"id": "b1", "name": "One", "nodes": [], "edges": []},
            {"id": "b1", "name": "Two", "nodes": [], "edges": []},
        ],
    }
    res = logged_in.put(URL, headers=h, json=bad)
    assert res.status_code == 400
