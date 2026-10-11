import shutil
from pathlib import Path

import pytest

from app.ai import context
from msklib.project import Project

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"
ALL = {"selection": True, "scene": True, "summary": True, "pov": True, "book": True}


@pytest.fixture()
def acts(tmp_path):
    shutil.copytree(FIX, tmp_path / "acts")
    p = Project.load(tmp_path / "acts")
    scene = next(i for i in p.outline.walk() if i.title == "Peter preaches")
    return p, scene


def test_includes_scene_book_and_pov_for_a_real_scene(acts):
    p, scene = acts
    scene.meta["POV"] = str(p.characters[0].id)
    scene.meta["summarySentence"] = "Peter addresses the crowd"
    text = context.build(p, ALL, scene.id, 100_000)
    assert "### Current scene: Peter preaches" in text and scene.text.strip()[:30] in text
    assert "Peter addresses the crowd" in text
    assert f"Name: {p.characters[0].name}" in text
    assert "Title: The Acts of the Apostles" in text


def test_every_source_can_be_switched_off(acts):
    p, scene = acts
    scene.meta["POV"] = str(p.characters[0].id)
    off = {k: False for k in ALL}
    assert context.build(p, off, scene.id, 100_000) == ""
    only_book = context.build(p, {**off, "book": True}, scene.id, 100_000)
    assert only_book.startswith("### Book info") and "Current scene" not in only_book


def test_no_scene_means_book_info_only_and_never_an_error(acts):
    p, scene = acts
    for sid in (None, 999_999, p.outline.children[0].id):  # none, unknown, a folder
        text = context.build(p, ALL, sid, 100_000)
        assert "Current scene" not in text and "### Book info" in text


def test_unknown_or_non_numeric_pov_is_ignored(acts):
    p, scene = acts
    for pov in ("", "0x", "Peter", "99999"):
        scene.meta["POV"] = pov
        assert "POV character" not in context.build(p, ALL, scene.id, 100_000)


def test_token_budget_trims_the_scene_but_keeps_its_end(acts):
    p, scene = acts
    scene.text = "start " + "word " * 5000 + "THE-END"
    text = context.build(p, {"scene": True}, scene.id, 600)
    assert text.startswith("### Current scene") and "[...]" in text
    assert text.endswith("THE-END") and "start" not in text
    assert len(text) < 3000


def test_parts_that_do_not_fit_are_dropped_not_truncated(acts):
    p, scene = acts
    assert context.build(p, {"book": True}, scene.id, 5) == ""  # nothing can fit; no half sentences


def test_order_is_stable(acts):
    p, scene = acts
    scene.meta["POV"] = str(p.characters[0].id)
    scene.meta["summarySentence"] = "x"
    headings = [ln for ln in context.build(p, ALL, scene.id, 100_000).split("\n") if ln.startswith("### ")]
    assert [h.split(":")[0] for h in headings] == [
        "### Current scene", "### Scene summary", "### POV character", "### Book info"]
