"""Mutate with msklib, then open the result in the real desktop Manuskript (offscreen).

Skipped when the desktop fork is not available (set MSK_DESKTOP_FORK / MSK_DESKTOP_PYTHON).
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from msklib.model import Item
from msklib.project import Project
from msklib.records import Character, Label

FORK = Path(os.environ.get("MSK_DESKTOP_FORK", "/home/ab/workspaces/manuskript-ai/manuskript"))
PY = Path(os.environ.get("MSK_DESKTOP_PYTHON", "/home/ab/workspaces/manuskript-ai/venv/bin/python"))
TOOL = Path(__file__).parent.parent / "tools" / "desktop_crosscheck.py"
FIX = Path(__file__).parent / "fixtures"

pytestmark = pytest.mark.skipif(not (FORK.is_dir() and PY.exists()),
                                reason="desktop Manuskript fork not available")


def desktop_view(root: Path, tmp_path: Path) -> dict:
    env = {**os.environ, "HOME": str(tmp_path / "home"), "QT_QPA_PLATFORM": "offscreen"}
    (tmp_path / "home").mkdir(exist_ok=True)
    out = subprocess.run([str(PY), str(TOOL), str(FORK), str(root)], env=env, capture_output=True,
                         text=True, timeout=180)
    assert "@@JSON@@" in out.stdout, out.stdout[-500:] + out.stderr[-500:]
    return json.loads(out.stdout.split("@@JSON@@", 1)[1])


def test_desktop_opens_mutated_project(tmp_path):
    root = tmp_path / "acts"
    shutil.copytree(FIX / "book-of-acts", root)
    shutil.copy(FIX / "book-of-acts.msk", tmp_path / "acts.msk")

    p = Project.load(root)
    walk = list(p.outline.walk())
    ch2 = next(i for i in walk if i.title == "Chapter 2")
    ch4 = next(i for i in walk if i.title == "Chapter 4")
    peter = next(i for i in walk if i.title == "Peter preaches")
    peter.parent.children.remove(peter)            # move a scene to another chapter
    peter.parent = ch4
    ch4.children.append(peter)
    ch2.children.reverse()                         # reorder
    ch2.title = "Chapter Two"                      # rename a folder
    next_id = max(i.id for i in walk) + 1
    ch4.children.append(Item(id=next_id, title="Brand: new", meta={"compile": "2"},
                             text="Hello world\nsecond line", parent=ch4))
    p.characters.append(Character(id=6, name="Silas (the scribe)", importance="1", color="#112233",
                                  infos=[("Age", "40")]))
    p.characters[0].name = "Simon Peter"
    p.labels.append(Label("Draft", "#abcdef"))
    p.status.append("Published")
    p.save()

    view = desktop_view(root, tmp_path)
    by_id = {i["id"]: i for i in view["items"]}
    mine = {i.id: i for i in Project.load(root).outline.walk()}
    assert sorted(by_id) == sorted(mine)
    assert by_id[next_id]["title"] == "Brand: new" and by_id[next_id]["words"] == 4
    assert by_id[ch2.id]["title"] == "Chapter Two"
    assert [i["id"] for i in view["items"]] == [i.id for i in Project.load(root).outline.walk()]
    assert (6, "Silas (the scribe)") in [(c["id"], c["name"]) for c in view["characters"]]
    assert (0, "Simon Peter") in [(c["id"], c["name"]) for c in view["characters"]]
    assert view["labels"][-1] == "Draft" and view["status"][-1] == "Published"

    # Desktop's own save of what we wrote should only add data it derives itself, and
    # reloading in msklib afterwards must still agree with desktop.
    after = Project.load(root)
    assert {i.id for i in after.outline.walk()} == set(mine)
    assert next(i for i in after.outline.walk() if i.id == peter.id).parent.title == "Chapter 4"
