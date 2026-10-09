import pytest

from msklib.project import Project


def test_create_blank_project(tmp_path):
    root = tmp_path / "My Novel"
    p = Project.create(root, "My Novel", "Ab")
    assert (tmp_path / "My Novel.msk").read_text() == "1"
    assert (root / "MANUSKRIPT").read_text() == "1"
    again = Project.load(root)
    assert again.infos["Title"] == "My Novel" and again.infos["Author"] == "Ab"
    assert [i.title for i in again.outline.walk()] == ["Draft", "Chapter 1"]
    assert [lb.name for lb in again.labels][0] == "Idea"
    assert again.next_id() == 3 and again.find(2).title == "Chapter 1"
    assert again.save() == []


def test_create_refuses_existing(tmp_path):
    Project.create(tmp_path / "a", "a")
    with pytest.raises(FileExistsError):
        Project.create(tmp_path / "a", "a")
