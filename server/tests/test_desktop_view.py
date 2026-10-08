"""msklib must see the same project as the real desktop Manuskript.

The JSON files were produced by tools/desktop_crosscheck.py (desktop loading the fixture
offscreen). To regenerate them see that script's docstring.
"""

import hashlib
import json
from pathlib import Path

import pytest

from msklib.counts import item_counts
from msklib.project import Project

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("name", ["book-of-acts", "draft-0001"])
def test_matches_desktop_load(name):
    desktop = json.loads((FIXTURES / f"desktop_view_{name}.json").read_text())
    p = Project.load(FIXTURES / name)
    ours = {i.id: i for i in p.outline.walk()}
    assert sorted(ours) == sorted(d["id"] for d in desktop["items"])
    for d in desktop["items"]:
        item = ours[d["id"]]
        assert (item.title, item.type) == (d["title"], d["type"])
        words, chars = item_counts(item)
        assert (words, chars) == (d["words"], d["chars"]), item.title
        if d["text_sha256"] is not None:
            assert hashlib.sha256(item.text.encode("utf8")).hexdigest() == d["text_sha256"]
    assert [(c.id, c.name) for c in p.characters] == [(c["id"], c["name"]) for c in desktop["characters"]]
    assert [lb.name for lb in p.labels] == desktop["labels"]
    assert p.status == desktop["status"]
    assert len(p.plots) == desktop["plots"]


@pytest.mark.parametrize("name", ["book-of-acts", "draft-0001"])
def test_item_order_matches_desktop(name):
    desktop = json.loads((FIXTURES / f"desktop_view_{name}.json").read_text())
    p = Project.load(FIXTURES / name)
    assert [i.id for i in p.outline.walk()] == [d["id"] for d in desktop["items"]]
