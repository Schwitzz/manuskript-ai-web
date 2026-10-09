"""Guards against quadratic behaviour in large folders (found by tools/bench_scale.py).

Counts work instead of measuring time, so it cannot flake on a slow machine."""

from msklib import model
from msklib.model import Item
from msklib.project import Project


def big_project(tmp_path, n):
    p = Project.create(tmp_path / "big", "Big")
    root = p.outline.children[0]
    for i in range(n):
        root.children.append(Item(id=p.next_id(), title=f"Scene {i}", meta={"compile": "2"},
                                  text=f"body {i}", parent=root))
    p.save()
    return Project.load(tmp_path / "big")


def count_slugify_calls(monkeypatch):
    calls = [0]
    real = model.slugify

    def counting(name):
        calls[0] += 1
        return real(name)

    monkeypatch.setattr(model, "slugify", counting)
    return calls


def test_naming_work_grows_linearly_with_folder_size(tmp_path, monkeypatch):
    small, large = 50, 400
    results = {}
    for n in (small, large):
        p = big_project(tmp_path / str(n), n) if (tmp_path / str(n)).mkdir() is None else None
        next(i for i in p.outline.walk() if i.title == "Scene 3").text += " edit"
        calls = count_slugify_calls(monkeypatch)
        p.save()
        results[n] = calls[0]
        monkeypatch.undo()
    # 8x the scenes must cost about 8x the naming work, not 64x.
    assert results[large] < results[small] * (large / small) * 2, results


def test_names_are_cached_within_one_save_and_refreshed_after_edits(tmp_path):
    p = big_project(tmp_path, 30)
    folder = p.outline.children[0]
    first = folder.child_names()
    assert folder.child_names() is first            # cached
    folder.children[0].title = "Renamed"
    p.save()                                        # save drops the cache
    assert folder.child_names() is not first
    assert "Renamed" in folder.child_names()[id(folder.children[0])]
    assert Project.load(tmp_path / "big").save() == []


def test_reorder_and_rename_are_never_served_from_a_stale_cache(tmp_path):
    p = big_project(tmp_path, 12)
    folder = p.outline.children[0]
    folder.child_names()                            # warm the cache
    folder.children.reverse()
    folder.children[0].title = "First now"
    p.save()
    again = Project.load(tmp_path / "big")
    got = [c.title for c in again.outline.children[0].children]
    assert got == [c.title for c in folder.children] and got[0] == "First now"
    assert again.save() == []
