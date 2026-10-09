"""Measure the costs that decide whether a search index / write queue is needed.

    cd server && uv run python tools/bench_scale.py [scenes] [kb_per_scene]
"""

import random
import re
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from msklib.model import Item  # noqa: E402
from msklib.project import Project  # noqa: E402

SCENES = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
KB = int(sys.argv[2]) if len(sys.argv) > 2 else 5
WORDS = "the lame man ran to Peter and John in the porch greatly wondering about faith".split()


def ms(t0):
    return (time.perf_counter() - t0) * 1000


with tempfile.TemporaryDirectory() as t:
    p = Project.create(Path(t) / "big", "Big")
    root = p.outline.children[0]
    rnd = random.Random(1)
    for n in range(SCENES):
        body = " ".join(rnd.choice(WORDS) for _ in range(KB * 1024 // 5))
        root.children.append(Item(id=p.next_id(), title=f"Scene {n}", meta={"compile": "2"},
                                  text=body, parent=root))
    t0 = time.perf_counter()
    p.save()
    print(f"{SCENES} scenes x {KB} KB: first save {ms(t0):.0f} ms")

    t0 = time.perf_counter()
    p = Project.load(Path(t) / "big")
    load = ms(t0)
    print(f"load whole project:                 {load:7.1f} ms")

    pattern = re.compile(re.escape("greatly wondering"), re.IGNORECASE)
    t0 = time.perf_counter()
    hits = sum(len(pattern.findall(i.text)) for i in p.outline.walk() if not i.is_folder)
    print(f"search scan over loaded text:       {ms(t0):7.1f} ms ({hits} matches)")
    print(f"search request (load + scan):       {load + ms(t0):7.1f} ms")

    s = next(i for i in p.outline.walk() if i.title == "Scene 7")
    s.text += " edit"
    t0 = time.perf_counter()
    written = p.save()
    print(f"one autosave (save only):           {ms(t0):7.1f} ms ({len(written)} files)")
    runs = []
    for i in range(10):
        a = time.perf_counter()
        q = Project.load(Path(t) / "big")
        sc = next(x for x in q.outline.walk() if x.title == "Scene 7")
        sc.text += f" {i}"
        q.save()
        runs.append(ms(a))
    print(f"one autosave request (load + save): {sum(runs) / len(runs):7.1f} ms")
