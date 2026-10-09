"""Scene revisions (revisions.xml), compatible with desktop Manuskript.

Desktop keeps the PREVIOUS text of a scene every time it changes, then thins old ones out
with the rules in settings.txt (`revisions.rules`: {span seconds or null: min gap seconds}).
We edit the existing XML in place so anything else in the file is preserved.
"""

from __future__ import annotations

import json
import re

from lxml import etree as ET

_PARSER = ET.XMLParser(huge_tree=True, remove_blank_text=True)
_INVALID = re.compile("[^\u0020-\uD7FF\u0009\u000A\u000D\uE000-\uFFFD\U00010000-\U0010FFFF]+")
_FAR = 60 * 60 * 24 * 30 * 365  # sort key for the "null" (everything older) rule

DEFAULT_RULES: dict[int | None, float] = {
    2592000: 86400.0, 3600: 600.0, 600: 60.0, 86400: 3600.0, None: 604800.0}


def xml_clean(text: str) -> str:
    return _INVALID.sub("", text)


def read_settings(settings_text: str) -> tuple[bool, bool, dict[int | None, float]]:
    """(keep, smartremove, rules) from the text of settings.txt."""
    try:
        rev = json.loads(settings_text).get("revisions", {})
    except ValueError:
        rev = {}
    rules = {(None if k in ("null", None) else int(k)): float(v)
             for k, v in rev.get("rules", {}).items()} or dict(DEFAULT_RULES)
    return bool(rev.get("keep", True)), bool(rev.get("smartremove", True)), rules


def thin(revs: list[tuple[int, str]], rules: dict[int | None, float], now: float):
    """Desktop's cleanRevisions: keep one revision per `rules[span]` seconds inside each span."""
    buckets: dict[int | None, list] = {span: [] for span in rules}
    for r in revs:
        for span in sorted(rules, key=lambda x: x if x else _FAR):
            if not span or now - r[0] < span:
                buckets[span].append(r)
                break
    kept = []
    for span, items in buckets.items():
        last = None
        for r in sorted(items, key=lambda x: x[0]):
            if last is None or r[0] - last >= rules[span]:
                kept.append(r)
                last = r[0]
    return sorted(kept, key=lambda x: x[0])


class Revisions:
    """All revisions of a project, loaded from / written back to revisions.xml."""

    def __init__(self, raw: bytes | None):
        self.root = ET.fromstring(raw, _PARSER) if raw else ET.Element(
            "outlineItem", title="Root", ID="0", type="folder", compile="2", lastPath="")
        self.dirty = False

    def _element(self, item_id: int, title: str = "", kind: str = "md", path: str = ""):
        for el in self.root.iter("outlineItem"):
            if el.get("ID") == str(item_id):
                return el
        el = ET.SubElement(self.root, "outlineItem", title=title, ID=str(item_id), type=kind,
                           compile="2", lastPath=path)
        return el

    def get(self, item_id: int) -> list[tuple[int, str]]:
        for el in self.root.iter("outlineItem"):
            if el.get("ID") == str(item_id):
                return [(int(r.get("timestamp")), r.get("text", ""))
                        for r in el if r.tag == "revision"]
        return []

    def set(self, item_id: int, revs: list[tuple[int, str]], title="", kind="md", path=""):
        el = self._element(item_id, title, kind, path)
        for r in [c for c in el if c.tag == "revision"]:
            el.remove(r)
        first_child = next((i for i, c in enumerate(el) if c.tag == "outlineItem"), len(el))
        for n, (ts, text) in enumerate(revs):
            r = ET.Element("revision", timestamp=str(int(ts)), text=xml_clean(text))
            el.insert(first_child + n, r)
        self.dirty = True

    def add(self, item_id: int, old_text: str, now: float, rules, smart: bool, **meta):
        revs = self.get(item_id) + [(int(now), old_text)]
        self.set(item_id, thin(revs, rules, now) if smart else revs, **meta)

    def drop_item(self, item_id: int):
        for el in list(self.root.iter("outlineItem")):
            if el.get("ID") == str(item_id) and el is not self.root:
                el.getparent().remove(el)
                self.dirty = True

    def tobytes(self) -> bytes:
        return ET.tostring(self.root, encoding="UTF-8", xml_declaration=True, pretty_print=True)
