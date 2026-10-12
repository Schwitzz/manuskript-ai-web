"""Tests for the whiteboard layout storage endpoints."""
import json
import shutil
from pathlib import Path

from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"


def setup(client, tmp_path, name="acts"):
    shutil.copytree(FIX, tmp_path / "projects" / name)
    shutil.copy(FIX.parent / "book-of-acts.msk", tmp_path / "projects" / f"{name}.msk")
    return csrf_headers(client)


def test_missing_project_returns_404(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    r = logged_in.get("/api/projects/nonexistent/whiteboard", headers=h)
    assert r.status_code == 404


def test_missing_layout_returns_empty(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    r = logged_in.get("/api/projects/acts/whiteboard", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == 1
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data["viewport"] == {"x": 0, "y": 0, "zoom": 1}


def test_valid_layout_persists(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    layout = {
        "version": 1,
        "nodes": [
            {"id": "1", "position": {"x": 100, "y": 200}},
            {"id": "2", "position": {"x": 300, "y": 400}},
        ],
        "edges": [
            {"id": "e1", "source": "1", "target": "2"},
        ],
        "viewport": {"x": 10, "y": 20, "zoom": 1.5},
    }
    r = logged_in.put("/api/projects/acts/whiteboard", headers=h, json=layout)
    assert r.status_code == 200
    assert r.json() == layout

    # Verify it was written to disk
    wb_file = tmp_path / "projects/acts/.whiteboards/layout.json"
    assert wb_file.exists()
    on_disk = json.loads(wb_file.read_text())
    assert on_disk == layout

    # Verify GET returns the same data
    r2 = logged_in.get("/api/projects/acts/whiteboard", headers=h)
    assert r2.status_code == 200
    assert r2.json() == layout


def test_oversized_layout_returns_413(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    # Create a layout that exceeds 5 MB
    big_nodes = [{"id": str(i), "position": {"x": i, "y": i}, "data": "x" * 1000} for i in range(6000)]
    layout = {"version": 1, "nodes": big_nodes, "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}}
    r = logged_in.put("/api/projects/acts/whiteboard", headers=h, json=layout)
    assert r.status_code == 413


def test_put_overwrites_previous_layout(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    layout1 = {"version": 1, "nodes": [{"id": "1", "position": {"x": 10, "y": 10}}], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}}
    logged_in.put("/api/projects/acts/whiteboard", headers=h, json=layout1)

    layout2 = {"version": 1, "nodes": [{"id": "2", "position": {"x": 20, "y": 20}}], "edges": [], "viewport": {"x": 5, "y": 5, "zoom": 2}}
    r = logged_in.put("/api/projects/acts/whiteboard", headers=h, json=layout2)
    assert r.status_code == 200

    r2 = logged_in.get("/api/projects/acts/whiteboard", headers=h)
    assert r2.json() == layout2


def test_layout_file_is_in_dot_folder(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    layout = {"version": 1, "nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}}
    logged_in.put("/api/projects/acts/whiteboard", headers=h, json=layout)

    # The file must be in .whiteboards/ (dot-folder), not in a visible folder
    wb_dir = tmp_path / "projects/acts/.whiteboards"
    assert wb_dir.is_dir()
    assert (wb_dir / "layout.json").exists()