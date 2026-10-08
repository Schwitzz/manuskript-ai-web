"""Property tests: arbitrary text must survive save -> load, and a second save writes nothing."""

import shutil
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from msklib.model import Item
from msklib.project import Project
from msklib.records import Character

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"

# Everything except surrogates (not encodable) and \r (universal newlines turn it into \n on
# read, exactly like the desktop). Includes colons, tabs, no-break and exotic spaces.
SAFE = st.characters(blacklist_categories=("Cs",), blacklist_characters="\r\x00")
ODD = st.sampled_from([":", "\t", "\u00a0", "\u2003", "\u3000", "#", "/", "\\", '"', "_.._", "\u200b"])
TEXT = st.lists(st.one_of(SAFE, ODD), max_size=40).map("".join)
LINE = TEXT.map(lambda s: s.replace("\n", " "))
BODY = st.lists(st.one_of(SAFE, ODD, st.just("\n")), max_size=300).map("".join)

CFG = settings(max_examples=60, deadline=None,
               suppress_health_check=[HealthCheck.function_scoped_fixture])


def fresh(tmp_path_factory) -> Path:
    dest = tmp_path_factory.mktemp("prop") / "p"
    shutil.copytree(FIX, dest)
    return dest


@CFG
@given(title=LINE, body=BODY)
def test_scene_title_and_body_survive(tmp_path_factory, title, body):
    root = fresh(tmp_path_factory)
    p = Project.load(root)
    chapter = next(i for i in p.outline.walk() if i.title == "Chapter 3")
    new_id = max(i.id for i in p.outline.walk()) + 1
    chapter.children.append(Item(id=new_id, title=title, meta={"compile": "2"}, text=body,
                                 parent=chapter))
    p.save()

    again = Project.load(root)
    got = next(i for i in again.outline.walk() if i.id == new_id)
    assert got.text == body                      # body is byte exact
    assert got.title == title.lstrip()           # header values lose only leading blanks
    assert again.save() == []                    # and the file is now stable
    assert Project.load(root).save() == []


@CFG
@given(title=st.lists(LINE, min_size=1, max_size=4).map("\n".join))
def test_multiline_title_is_stable(tmp_path_factory, title):
    root = fresh(tmp_path_factory)
    p = Project.load(root)
    scene = next(i for i in p.outline.walk() if not i.is_folder)
    scene.title = title
    p.save()
    first = Project.load(root)
    assert first.save() == []
    second = Project.load(root)
    s1 = next(i for i in first.outline.walk() if i.id == scene.id)
    s2 = next(i for i in second.outline.walk() if i.id == scene.id)
    assert s1.title == s2.title and s1.text == scene.text


@CFG
@given(name=LINE, notes=TEXT, info_key=st.text(alphabet="abcXYZ :_", min_size=1, max_size=8),
       info_val=LINE)
def test_character_fields_are_stable(tmp_path_factory, name, notes, info_key, info_val):
    root = fresh(tmp_path_factory)
    p = Project.load(root)
    p.characters.append(Character(id=9, name=name, notes=notes, color="#123456",
                                  infos=[(info_key, info_val)]))
    p.save()
    again = Project.load(root)
    assert again.save() == []
    assert Project.load(root).save() == []
    got = next(c for c in again.characters if c.id == 9)
    assert got.color == "#123456"
