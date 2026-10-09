"""A write that dies half way must leave the old file intact and no stray temp files."""

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from msklib.project import Project

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"


@pytest.fixture()
def proj_dir(tmp_path):
    dest = tmp_path / "p"
    shutil.copytree(FIX, dest)
    return dest


def scene_file(root: Path) -> Path:
    return next((root / "outline").rglob("1-Peter_preaches.md"))


def test_failure_before_rename_keeps_old_file(proj_dir, monkeypatch):
    original = scene_file(proj_dir).read_bytes()
    p = Project.load(proj_dir)
    next(i for i in p.outline.walk() if i.title == "Peter preaches").text = "new body"

    def boom(src, dst):
        raise OSError("disk exploded")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        p.save()
    monkeypatch.undo()
    assert scene_file(proj_dir).read_bytes() == original
    assert not [f for f in proj_dir.rglob(".msk-*")], "temp file left behind"


def test_process_killed_mid_save_leaves_a_loadable_project(proj_dir):
    """SIGKILL the writer at a random point; every real file must still parse, and
    at most stale .msk-* temp files may remain (they are ignored on load)."""
    script = textwrap.dedent(f"""
        import os, signal, sys
        sys.path.insert(0, {str(Path(__file__).parent.parent)!r})
        from msklib.project import Project
        p = Project.load({str(proj_dir)!r})
        real = os.replace
        calls = [0]
        def die_on_tenth(a, b):
            calls[0] += 1
            if calls[0] == 10:
                os.kill(os.getpid(), signal.SIGKILL)
            return real(a, b)
        os.replace = die_on_tenth
        for it in p.outline.walk():
            if not it.is_folder:
                it.text += "\\nedited"
        p.save()
    """)
    proc = subprocess.run([sys.executable, "-c", script])
    assert proc.returncode == -9
    loaded = Project.load(proj_dir)
    scenes = [i for i in loaded.outline.walk() if not i.is_folder]
    assert len(scenes) == 41 and all(s.text for s in scenes)
    edited = sum(s.text.endswith("\nedited") for s in scenes)
    assert 0 < edited < 41  # a partial save: some files new, none corrupt
