import shutil
from pathlib import Path

import pytest

from msklib.legacy import html_to_text, modernise
from msklib.project import Project

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"
FOLDER = "outline/0-Jerusalem/0-Chapter_1"


def scene_file(kind: str, sid: int, name: str, body: str) -> str:
    return f"title:          {name}\nID:             {sid}\ntype:           {kind}\ncompile:        2\n\n\n{body}"


@pytest.fixture()
def proj(tmp_path):
    d = tmp_path / "p"
    shutil.copytree(FIX, d)
    (d / FOLDER / "3-Old_t2t.md").write_text(scene_file("t2t", 900, "Old t2t", "old body text"))
    (d / FOLDER / "4-Old_txt.md").write_text(scene_file("txt", 901, "Old txt", "plain body"))
    (d / FOLDER / "5-Html.md").write_text(
        scene_file("html", 902, "Html", "<p>Hello <b>world</b></p><p>Second &amp; last</p>"))
    return d


def test_html_to_text():
    assert html_to_text("<p>Hello <b>world</b></p><p>Second &amp; last</p>") == "Hello world\nSecond & last"
    assert html_to_text("a<br>b<br/>c") == "a\nb\nc"
    assert html_to_text("<style>p{x:y}</style><p>kept</p><script>alert(1)</script>") == "kept"
    assert html_to_text("plain") == "plain" and html_to_text("") == ""
    assert html_to_text("<ul><li>one</li><li>two</li></ul>") == "one\ntwo"


def test_modernise_types():
    assert modernise("t2t", "x", "n") == ("md", "x", "n")
    assert modernise("txt", "x", "") == ("md", "x", "")
    assert modernise("md", "<b>keep</b>", "") == ("md", "<b>keep</b>", "")      # md is never touched
    assert modernise("html", "<b>x</b>", "<i>n</i>") == ("md", "x", "n")


def test_legacy_scenes_load_as_markdown(proj):
    p = Project.load(proj)
    got = {i.id: i for i in p.outline.walk()}
    assert [got[i].type for i in (900, 901, 902)] == ["md", "md", "md"]
    assert got[900].text == "old body text" and got[901].text == "plain body"
    assert got[902].text == "Hello world\nSecond & last"


def test_conversion_is_saved_and_the_original_is_kept_as_a_revision(proj):
    p = Project.load(proj)
    written = p.save()
    assert f"{FOLDER}/3-Old_t2t.md" in written and f"{FOLDER}/5-Html.md" in written
    assert "type:           md" in (proj / FOLDER / "5-Html.md").read_text()
    from msklib.revisions import Revisions
    revs = Revisions((proj / "revisions.xml").read_bytes()).get(902)
    assert revs and revs[-1][1] == "<p>Hello <b>world</b></p><p>Second &amp; last</p>"
    again = Project.load(proj)
    assert again.save() == []                      # now stable
    assert {i.id: i.type for i in again.outline.walk()}[902] == "md"


def test_md_scenes_with_html_inside_are_never_converted(tmp_path):
    d = tmp_path / "p"
    shutil.copytree(FIX, d)
    (d / FOLDER / "3-Keep.md").write_text(scene_file("md", 910, "Keep", "<p>real html in markdown</p>"))
    p = Project.load(d)
    assert next(i for i in p.outline.walk() if i.id == 910).text == "<p>real html in markdown</p>"
    assert p.save() == []


def test_desktop_agrees_on_the_converted_text(proj, tmp_path):
    import json, os, subprocess
    fork = Path("/home/ab/workspaces/manuskript-ai/manuskript")
    py = Path("/home/ab/workspaces/manuskript-ai/venv/bin/python")
    if not (fork.is_dir() and py.exists()):
        pytest.skip("desktop fork not available")
    work = tmp_path / "d"
    work.mkdir()
    shutil.move(str(proj), work / "acts")
    shutil.copy(FIX.parent / "book-of-acts.msk", work / "acts.msk")
    env = {**os.environ, "HOME": str(tmp_path / "h"), "QT_QPA_PLATFORM": "offscreen"}
    (tmp_path / "h").mkdir()
    tool = Path(__file__).parent.parent / "tools" / "desktop_crosscheck.py"
    out = subprocess.run([str(py), str(tool), str(fork), str(work / "acts")], env=env,
                         capture_output=True, text=True, timeout=180).stdout
    view = json.loads(out.split("@@JSON@@", 1)[1])
    by_id = {i["id"]: i for i in view["items"]}
    ours = {i.id: i for i in Project.load(work / "acts").outline.walk()}
    for sid in (900, 901, 902):
        assert by_id[sid]["type"] == "md"
    assert by_id[900]["words"] == 3 and by_id[901]["words"] == 2
    assert ours[900].text == "old body text"
