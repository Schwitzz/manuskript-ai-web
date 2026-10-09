import shutil
import zipfile
from pathlib import Path

import pytest

from msklib.project import Project

FIXTURES = Path(__file__).parent / "fixtures"


def zip_project(src: Path, dest: Path, crlf: bool = False) -> Path:
    """A desktop-style zipped .msk: files at the zip root."""
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src.rglob("*")):
            if f.is_file():
                data = f.read_bytes()
                if crlf and f.suffix in (".txt", ".md"):
                    data = data.replace(b"\n", b"\r\n")
                zf.writestr(f.relative_to(src).as_posix(), data)
    return dest


@pytest.mark.parametrize("name", ["book-of-acts", "draft-0001"])
def test_zip_loads_the_same_project_as_the_folder(tmp_path, name):
    z = zip_project(FIXTURES / name, tmp_path / f"{name}.msk")
    from_zip = Project.load_zip(z)
    from_dir = Project.load(FIXTURES / name)
    assert [(i.id, i.title, i.text) for i in from_zip.outline.walk()] == \
           [(i.id, i.title, i.text) for i in from_dir.outline.walk()]
    assert [c.name for c in from_zip.characters] == [c.name for c in from_dir.characters]
    assert from_zip.infos == from_dir.infos and from_zip.status == from_dir.status
    assert len(from_zip.plots) == len(from_dir.plots) and len(from_zip.world) == len(from_dir.world)


def test_zip_is_read_only(tmp_path):
    p = Project.load_zip(zip_project(FIXTURES / "book-of-acts", tmp_path / "a.msk"))
    next(i for i in p.outline.walk() if not i.is_folder).text = "changed"
    with pytest.raises(Project.ReadOnlyError):
        p.save()


def test_zip_with_windows_line_endings_reads_clean(tmp_path):
    z = zip_project(FIXTURES / "book-of-acts", tmp_path / "a.msk", crlf=True)
    p = Project.load_zip(z)
    assert all("\r" not in i.text for i in p.outline.walk())
    ref = Project.load(FIXTURES / "book-of-acts")
    assert [i.text for i in p.outline.walk()] == [i.text for i in ref.outline.walk()]


def test_extract_to_makes_an_editable_folder_project(tmp_path):
    z = zip_project(FIXTURES / "book-of-acts", tmp_path / "a.msk")
    folder = Project.load_zip(z).extract_to(tmp_path / "acts")
    assert Project.load(tmp_path / "acts").save() == []
    scene = next(i for i in folder.outline.walk() if i.title == "Peter preaches")
    scene.text += "\nmore"
    assert folder.save()
    with pytest.raises(FileExistsError):
        Project.load_zip(z).extract_to(tmp_path / "acts")


def test_rejects_zips_that_are_not_v1_projects_or_are_unsafe(tmp_path):
    old = tmp_path / "old.msk"
    with zipfile.ZipFile(old, "w") as zf:
        zf.writestr("outline.xml", "<x/>")
    with pytest.raises(ValueError, match="MANUSKRIPT"):
        Project.load_zip(old)
    evil = tmp_path / "evil.msk"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("MANUSKRIPT", "1")
        zf.writestr("../escape.txt", "x")
    with pytest.raises(ValueError, match="Unsafe"):
        Project.load_zip(evil)


@pytest.mark.parametrize("bad", ["../x.txt", "a/../../x.txt", "/abs.txt", "a\\..\\b.txt"])
def test_unsafe_names_are_rejected_not_skipped(tmp_path, bad):
    z = tmp_path / "e.msk"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("MANUSKRIPT", "1")
        zf.writestr(bad, "x")
    with pytest.raises(ValueError, match="Unsafe"):
        Project.load_zip(z)


def test_dot_entries_are_skipped_like_dot_files_in_folders(tmp_path):
    z = tmp_path / "d.msk"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("MANUSKRIPT", "1")
        zf.writestr(".trash/old.md", "title: x\nID: 9\ntype: md\n\n\nbody")
    assert list(Project.load_zip(z).outline.walk()) == []
