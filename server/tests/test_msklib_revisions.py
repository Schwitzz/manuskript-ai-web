import json
import shutil
import time
from pathlib import Path

import pytest

from msklib.project import Project
from msklib.revisions import DEFAULT_RULES, Revisions, read_settings, thin

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def proj_dir(tmp_path):
    dest = tmp_path / "p"
    shutil.copytree(FIXTURES / "book-of-acts", dest)
    return dest


def scene(p, title="Peter preaches"):
    return next(i for i in p.outline.walk() if i.title == title)


def test_revisions_file_roundtrips_byte_for_byte():
    for name in ("book-of-acts", "draft-0001"):
        raw = (FIXTURES / name / "revisions.xml").read_bytes()
        assert Revisions(raw).tobytes() == raw


def test_edit_keeps_previous_text_as_revision(proj_dir):
    p = Project.load(proj_dir)
    s = scene(p)
    old = s.text
    s.text = old + "\nchanged"
    p.save()
    raw = (proj_dir / "revisions.xml").read_bytes()
    revs = Revisions(raw).get(s.id)
    assert revs[-1][1] == old and abs(revs[-1][0] - time.time()) < 5
    assert Project.load(proj_dir).save() == []


def test_no_text_change_no_revision(proj_dir):
    before = (proj_dir / "revisions.xml").read_bytes()
    p = Project.load(proj_dir)
    scene(p).meta["label"] = "2"
    p.save()
    assert (proj_dir / "revisions.xml").read_bytes() == before


def test_keep_false_writes_no_revisions(proj_dir):
    settings = json.loads((proj_dir / "settings.txt").read_text())
    settings["revisions"]["keep"] = False
    (proj_dir / "settings.txt").write_text(json.dumps(settings, indent=4, sort_keys=True))
    before = (proj_dir / "revisions.xml").read_bytes()
    p = Project.load(proj_dir)
    scene(p).text += "x"
    p.save()
    assert (proj_dir / "revisions.xml").read_bytes() == before


def test_new_project_gets_revisions_file_on_first_edit(tmp_path):
    p = Project.create(tmp_path / "n", "N")
    p.outline.children[0].children[0].text = "first"
    p.save()
    revs = Revisions((tmp_path / "n/revisions.xml").read_bytes()).get(2)
    assert revs and revs[-1][1] == ""  # the blank scene's previous text
    assert Project.load(tmp_path / "n").save() == []


def test_edits_within_a_minute_collapse_like_desktop(tmp_path):
    """Desktop thins revisions to one per 60 s in the last 10 minutes (smartremove)."""
    p = Project.create(tmp_path / "n", "N")
    s = p.outline.children[0].children[0]
    for text in ("one", "two", "three"):
        s.text = text
        p.save()
    assert len(Revisions((tmp_path / "n/revisions.xml").read_bytes()).get(2)) == 1


def test_smartremove_off_keeps_every_revision(tmp_path):
    p = Project.create(tmp_path / "n", "N")
    cfg = json.loads((tmp_path / "n/settings.txt").read_text())
    cfg["revisions"] = {"keep": True, "smartremove": False}
    (tmp_path / "n/settings.txt").write_text(json.dumps(cfg, indent=4, sort_keys=True))
    p = Project.load(tmp_path / "n")
    s = p.outline.children[0].children[0]
    for text in ("one", "two", "three"):
        s.text = text
        p.save()
    texts = [t for _ts, t in Revisions((tmp_path / "n/revisions.xml").read_bytes()).get(2)]
    assert texts == ["", "one", "two"]


def test_invalid_xml_characters_are_stripped():
    r = Revisions(None)
    r.set(5, [(100, "ok\x00\x0b text")])
    assert Revisions(r.tobytes()).get(5) == [(100, "ok text")]


def test_thinning_matches_desktop_rules():
    now = 1_000_000.0
    rules = {**DEFAULT_RULES}
    # 20 edits, 5 seconds apart, all within the last 10 minutes: one per 60 s survives.
    revs = [(int(now - 100 + i * 5), f"v{i}") for i in range(20)]
    kept = thin(revs, rules, now)
    assert 1 < len(kept) < len(revs)
    gaps = [b[0] - a[0] for a, b in zip(kept, kept[1:])]
    assert all(g >= 60 for g in gaps)
    # very old revisions fall under the null rule: one per week
    old = [(int(now - 365 * 86400 + i * 3600), f"o{i}") for i in range(48)]
    assert len(thin(old, rules, now)) <= 2


def test_read_settings_variants():
    assert read_settings("not json") == (True, True, DEFAULT_RULES)
    keep, smart, rules = read_settings(json.dumps({"revisions": {"keep": False, "smartremove": False,
                                                                 "rules": {"60": 5, "null": 99}}}))
    assert (keep, smart, rules) == (False, False, {60: 5.0, None: 99.0})


def test_deleted_scene_revisions_are_dropped(proj_dir):
    p = Project.load(proj_dir)
    s = scene(p)
    s.text += "\nx"
    p.save()
    p2 = Project.load(proj_dir)
    s2 = scene(p2)
    s2.parent.children.remove(s2)
    p2.save()
    assert Revisions((proj_dir / "revisions.xml").read_bytes()).get(s.id) == []
