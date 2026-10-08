import shutil
from pathlib import Path

import pytest

from msklib.project import Project

FIXTURES = Path(__file__).parent / "fixtures"
FIX = FIXTURES / "book-of-acts"


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


def test_edit_one_scene_changes_only_that_scene_and_its_ancestor_folders(proj_dir):
    before = snapshot(proj_dir)
    p = Project.load(proj_dir)
    scene = next(i for i in p.outline.walk() if i.title == "Peter preaches")
    scene.text += "\nAn added line."
    written = p.save()
    after = snapshot(proj_dir)
    changed = sorted(k for k in after if before.get(k) != after[k])
    # Like desktop, charCount is refreshed on the scene and on every folder above it.
    assert sorted(written) == changed == sorted([
        "outline/0-Jerusalem/2-Chapter_3/1-Peter_preaches.md",
        "outline/0-Jerusalem/2-Chapter_3/folder.txt",
        "outline/0-Jerusalem/folder.txt"])
    assert after["outline/0-Jerusalem/2-Chapter_3/1-Peter_preaches.md"].endswith(b"An added line.")
    assert Project.load(proj_dir).save() == []


def test_reload_after_edit_matches(proj_dir):
    p = Project.load(proj_dir)
    scene = next(i for i in p.outline.walk() if i.title == "Peter preaches")
    scene.text = "New body\n\nsecond paragraph"
    p.save()
    again = Project.load(proj_dir)
    s2 = next(i for i in again.outline.walk() if i.title == "Peter preaches")
    assert s2.text == "New body\n\nsecond paragraph" and s2.id == scene.id
    assert again.save() == []


@pytest.mark.parametrize("name", ["book-of-acts", "draft-0001"])
def test_golden_roundtrip_both_projects(tmp_path, name):
    dest = tmp_path / name
    shutil.copytree(FIXTURES / name, dest)
    before = snapshot(dest)
    p = Project.load(dest)
    assert p.save() == []
    assert snapshot(dest) == before


def test_records_are_parsed(proj_dir):
    p = Project.load(proj_dir)
    assert p.infos["Title"] == "The Acts of the Apostles"
    assert [c.name for c in p.characters][:2] == ["Peter", "Paul"]
    assert p.status == ["TODO", "First draft", "Second draft", "Final"]
    assert p.labels[0].name == "Idea" and p.labels[0].color == "#ffff00"


def test_rename_character_moves_file(proj_dir):
    p = Project.load(proj_dir)
    peter = p.characters[0]
    peter.name = "Simon Peter"
    written = p.save()
    assert written == ["characters/0-Simon_Peter.txt"]
    assert not (proj_dir / "characters/0-Peter.txt").exists()
    again = Project.load(proj_dir)
    assert again.characters[0].name == "Simon Peter" and again.save() == []


def test_add_character_label_status(proj_dir):
    from msklib.records import Character, Label
    p = Project.load(proj_dir)
    p.characters.append(Character(id=6, name="Silas: the scribe", importance="1", color="#112233",
                                  infos=[("Age", "40")]))
    p.labels.append(Label("Draft", "#abcdef"))
    p.status.append("Published")
    assert sorted(p.save()) == ["characters/6-Silas-_the_scribe.txt", "labels.txt", "status.txt"]
    again = Project.load(proj_dir)
    silas = again.characters[-1]
    assert silas.name == "Silas: the scribe" and silas.infos == [("Age", "40")]
    assert again.labels[-1].color == "#abcdef" and again.status[-1] == "Published"
    assert again.save() == []


def test_multiline_and_inner_special_chars_roundtrip(proj_dir):
    note = "line one\nline\u00a0two with nbsp\nthird\tline with tab\n\nafter blank"
    p = Project.load(proj_dir)
    p.characters[1].notes = note
    p.save()
    again = Project.load(proj_dir)
    # The blank line is written indented, so it stays part of the value (same as desktop).
    assert again.characters[1].notes == note
    assert again.save() == []


def test_leading_whitespace_on_continuation_lines_is_normalised(proj_dir):
    """The desktop parser strips continuation lines, so leading blanks are lost there too.
    After one save the file is stable."""
    p = Project.load(proj_dir)
    p.characters[1].notes = "first\n\u00a0indented"
    p.save()
    once = Project.load(proj_dir)
    assert once.characters[1].notes == "first\nindented"
    once.save()
    twice = Project.load(proj_dir)
    assert twice.save() == []


def test_delete_character_goes_to_trash(proj_dir):
    p = Project.load(proj_dir)
    gone = p.characters.pop()
    p.save()
    assert not (proj_dir / gone.path()).exists()
    assert (proj_dir / ".trash" / gone.path()).exists()


def test_plots_and_world_parsed(proj_dir):
    p = Project.load(proj_dir)
    assert [pl.name for pl in p.plots][0] == "The good news spreads from Jerusalem to Rome"
    assert p.plots[2].characters == [1, 5]
    assert [w.name for w in p.world] == ["Places", "Cultures", "Travel"]
    assert [c.name for c in p.world[0].children][:2] == ["Jerusalem", "Judea"]


def test_edit_plot_step_and_world_item(proj_dir):
    from msklib.xmlrecords import WorldItem
    p = Project.load(proj_dir)
    p.plots[0].steps.append({"name": "Final step", "ID": "0", "meta": "", "summary": "Rome"})
    p.plots[0].attrs["steps"] = "Resolution steps"
    p.plots[1].set_characters([0, 1])
    p.world[0].children.append(WorldItem({"name": "Antioch", "ID": "12"}))
    assert sorted(p.save()) == ["plots.xml", "world.opml"]
    again = Project.load(proj_dir)
    assert again.plots[0].steps[0]["name"] == "Final step"
    assert again.plots[1].characters == [0, 1]
    assert again.world[0].children[-1].name == "Antioch"
    assert again.save() == []
