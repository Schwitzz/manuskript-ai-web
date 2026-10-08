import shutil
from pathlib import Path

import pytest

from msklib.project import Project

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"


@pytest.fixture()
def proj_dir(tmp_path):
    dest = tmp_path / "book-of-acts"
    shutil.copytree(FIX, dest)
    return dest


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_loads_outline_tree(proj_dir):
    p = Project.load(proj_dir)
    top = [c.title for c in p.outline.children]
    assert top == ["Jerusalem", "Judea and Samaria", "To the extremities of the world"]
    scenes = [i for i in p.outline.walk() if not i.is_folder]
    assert len(scenes) == 41


def test_roundtrip_is_byte_identical(proj_dir):
    before = snapshot(proj_dir)
    p = Project.load(proj_dir)
    written = p.save()
    after = snapshot(proj_dir)
    assert written == [], f"unchanged project rewrote: {written[:5]}"
    assert before == after


def test_edit_one_scene_changes_only_that_file(proj_dir):
    before = snapshot(proj_dir)
    p = Project.load(proj_dir)
    scene = next(i for i in p.outline.walk() if i.title == "Peter preaches")
    scene.text += "\nAn added line."
    written = p.save()
    after = snapshot(proj_dir)
    changed = [k for k in after if before.get(k) != after[k]]
    assert len(written) == 1 and changed == written
    assert after[written[0]].endswith(b"An added line.")


def test_reload_after_edit_matches(proj_dir):
    p = Project.load(proj_dir)
    scene = next(i for i in p.outline.walk() if i.title == "Peter preaches")
    scene.text = "New body\n\nsecond paragraph"
    p.save()
    again = Project.load(proj_dir)
    s2 = next(i for i in again.outline.walk() if i.title == "Peter preaches")
    assert s2.text == "New body\n\nsecond paragraph" and s2.id == scene.id
    assert again.save() == []
