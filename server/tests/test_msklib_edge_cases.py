import shutil
from pathlib import Path

from msklib.project import Project
from msklib.xmlrecords import Plot, WorldItem, parse_plots, parse_world, render_plots, render_world

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"


def test_control_characters_in_plots_and_world_do_not_crash_saving():
    plots = parse_plots(render_plots([Plot({"name": "a\x0bb\x00c", "ID": "1"},
                                          steps=[{"name": "s\x1f", "summary": "x\x08y"}])]))
    assert plots[0].name == "abc" and plots[0].steps[0]["summary"] == "xy"
    world = parse_world(render_world([WorldItem({"name": "x\x00y", "ID": "1"})]))
    assert world[0].name == "xy"


def test_stray_files_in_outline_are_moved_to_trash_not_deleted(tmp_path):
    """Desktop Manuskript discards unknown files in outline/ on save. We do the same, but into
    .trash, so nothing a user dropped there is ever lost."""
    d = tmp_path / "p"
    shutil.copytree(FIX, d)
    (d / "outline/0-Jerusalem/readme.txt").write_text("my own notes file")
    (d / "outline/0-Jerusalem/0-Chapter_1/page.html").write_text("<p>x</p>")
    p = Project.load(d)
    assert not [i for i in p.outline.walk() if i.title in ("readme", "page")]
    p.save()
    assert not (d / "outline/0-Jerusalem/readme.txt").exists()
    assert (d / ".trash/outline/0-Jerusalem/readme.txt").read_text() == "my own notes file"
    assert (d / ".trash/outline/0-Jerusalem/0-Chapter_1/page.html").exists()
    assert Project.load(d).save() == []


def test_files_outside_outline_and_characters_are_left_alone(tmp_path):
    d = tmp_path / "p"
    shutil.copytree(FIX, d)
    (d / "notes.txt").write_text("project level note")
    (d / "research").mkdir()
    (d / "research/map.png").write_bytes(b"\x89PNG")
    p = Project.load(d)
    next(i for i in p.outline.walk() if not i.is_folder).text += "x"
    p.save()
    assert (d / "notes.txt").read_text() == "project level note"
    assert (d / "research/map.png").read_bytes() == b"\x89PNG"


def test_empty_optional_files_are_never_created(tmp_path):
    d = tmp_path / "p"
    shutil.copytree(FIX, d)
    for name in ("plots.xml", "world.opml", "summary.txt", "revisions.xml"):
        (d / name).unlink()
    p = Project.load(d)
    p.save()
    assert not (d / "plots.xml").exists() and not (d / "world.opml").exists()
    assert not (d / "revisions.xml").exists() and not (d / "summary.txt").exists()


def test_project_missing_files_still_opens(tmp_path):
    d = tmp_path / "p"
    d.mkdir()
    (d / "MANUSKRIPT").write_text("1")
    p = Project.load(d)
    assert list(p.outline.walk()) == [] and p.characters == [] and p.plots == []
    assert p.save() == []
