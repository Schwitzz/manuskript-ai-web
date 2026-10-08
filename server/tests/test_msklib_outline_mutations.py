import shutil
from pathlib import Path

import pytest

from msklib.model import Item
from msklib.project import Project

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"


@pytest.fixture()
def proj_dir(tmp_path):
    dest = tmp_path / "p"
    shutil.copytree(FIX, dest)
    return dest


def find(p: Project, title: str) -> Item:
    return next(i for i in p.outline.walk() if i.title == title)


def texts(p: Project) -> dict[int, str]:
    return {i.id: i.text for i in p.outline.walk() if not i.is_folder}


def md_files(root: Path) -> set[str]:
    return {str(f.relative_to(root)) for f in (root / "outline").rglob("*") if f.is_file()}


def test_rename_scene_moves_file_and_keeps_content(proj_dir):
    p = Project.load(proj_dir)
    before = texts(p)
    scene = find(p, "Peter preaches")
    old = scene.last_path
    scene.title = "Peter speaks"
    p.save()
    assert not (proj_dir / old).exists()
    again = Project.load(proj_dir)
    assert find(again, "Peter speaks").id == scene.id
    assert texts(again) == before
    assert again.save() == []


def test_rename_folder_moves_children(proj_dir):
    p = Project.load(proj_dir)
    before = texts(p)
    find(p, "Chapter 3").title = "Chapter Three"
    p.save()
    again = Project.load(proj_dir)
    assert texts(again) == before
    assert any("Chapter_Three" in f for f in md_files(proj_dir))
    assert not any("Chapter_3" in f for f in md_files(proj_dir))
    assert again.save() == []


def test_reorder_scenes_renumbers_files(proj_dir):
    p = Project.load(proj_dir)
    before = texts(p)
    chapter = find(p, "Chapter 2")
    chapter.children.reverse()
    p.save()
    again = Project.load(proj_dir)
    assert [c.title for c in find(again, "Chapter 2").children] == [c.title for c in chapter.children]
    assert texts(again) == before
    assert again.save() == []


def test_move_scene_to_another_folder(proj_dir):
    p = Project.load(proj_dir)
    before = texts(p)
    scene = find(p, "Peter preaches")
    scene.parent.children.remove(scene)
    target = find(p, "Chapter 4")
    scene.parent = target
    target.children.append(scene)
    p.save()
    again = Project.load(proj_dir)
    assert find(again, "Peter preaches").parent.title == "Chapter 4"
    assert texts(again) == before
    assert again.save() == []


def test_delete_scene_goes_to_trash(proj_dir):
    p = Project.load(proj_dir)
    scene = find(p, "Peter preaches")
    old = scene.last_path
    text = scene.text
    scene.parent.children.remove(scene)
    p.save()
    assert not (proj_dir / old).exists()
    trashed = list((proj_dir / ".trash").rglob("*Peter_preaches*"))
    assert len(trashed) == 1 and text in trashed[0].read_text(encoding="utf8")
    assert Project.load(proj_dir).save() == []  # .trash is ignored on load


def test_delete_folder_trashes_everything_inside(proj_dir):
    p = Project.load(proj_dir)
    chapter = find(p, "Chapter 2")
    count = len([c for c in chapter.walk()]) + 1
    chapter.parent.children.remove(chapter)
    p.save()
    assert len(list((proj_dir / ".trash").rglob("*.md"))) + len(
        list((proj_dir / ".trash").rglob("folder.txt"))) == count
    again = Project.load(proj_dir)
    assert "Chapter 2" not in [i.title for i in again.outline.walk()]
    assert again.save() == []


def test_add_scene_and_folder(proj_dir):
    p = Project.load(proj_dir)
    chapter = find(p, "Chapter 3")
    new_id = max(i.id for i in p.outline.walk()) + 1
    scene = Item(id=new_id, title="A new scene: with colon", type="md",
                 meta={"compile": "2"}, text="Fresh text\nline two", parent=chapter)
    chapter.children.append(scene)
    folder = Item(id=new_id + 1, title="Fresh folder", type="folder", meta={"compile": "2"},
                  parent=chapter)
    chapter.children.append(folder)
    p.save()
    again = Project.load(proj_dir)
    got = find(again, "A new scene: with colon")
    assert got.text == "Fresh text\nline two" and got.parent.title == "Chapter 3"
    assert find(again, "Fresh folder").is_folder
    assert again.save() == []


def test_duplicate_titles_get_unique_paths(proj_dir):
    p = Project.load(proj_dir)
    chapter = find(p, "Chapter 3")
    base = max(i.id for i in p.outline.walk()) + 1
    for n in range(2):
        chapter.children.append(Item(id=base + n, title="Same", meta={"compile": "2"},
                                     text=f"body {n}", parent=chapter))
    p.save()
    again = Project.load(proj_dir)
    same = [i for i in again.outline.walk() if i.title == "Same"]
    assert sorted(i.text for i in same) == ["body 0", "body 1"]
    assert again.save() == []


def test_unicode_and_odd_titles(proj_dir):
    p = Project.load(proj_dir)
    chapter = find(p, "Chapter 3")
    new_id = max(i.id for i in p.outline.walk()) + 1
    title = "Zażółć \u00a0gęślą jaźń / 日本語 \"quotes\" #1"
    chapter.children.append(Item(id=new_id, title=title, meta={"compile": "2"}, text="x",
                                 parent=chapter))
    p.save()
    again = Project.load(proj_dir)
    assert find(again, title).text == "x"
    assert again.save() == []
