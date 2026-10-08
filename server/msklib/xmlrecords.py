"""Plots (plots.xml) and world (world.opml), written the way the desktop does with lxml.

Attributes are kept in a dict in file order, so nothing the desktop wrote is lost or
reordered. New items get attributes in the desktop's enum order.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lxml import etree as ET

_PARSER = ET.XMLParser(huge_tree=True)

PLOT_ORDER = ["name", "ID", "importance", "characters", "description", "result", "steps", "summary"]
STEP_ORDER = ["name", "ID", "meta", "summary"]
WORLD_ORDER = ["name", "ID", "description", "passion", "conflict"]


def _ordered(attrs: dict[str, str], order: list[str], keep_empty: bool) -> dict[str, str]:
    out = {k: attrs[k] for k in order if k in attrs and (keep_empty or attrs[k])}
    for k, v in attrs.items():  # unknown attributes are preserved
        if k not in out and (keep_empty or v):
            out[k] = v
    return out


@dataclass
class Plot:
    attrs: dict[str, str] = field(default_factory=dict)
    steps: list[dict[str, str]] = field(default_factory=list)

    @property
    def id(self) -> int:
        return int(self.attrs.get("ID", "0") or 0)

    @property
    def name(self) -> str:
        return self.attrs.get("name", "")

    @property
    def characters(self) -> list[int]:
        raw = self.attrs.get("characters", "")
        return [int(c) for c in raw.split(",") if c.strip().isdigit()]

    def set_characters(self, ids: list[int]) -> None:
        if ids:
            self.attrs["characters"] = ",".join(str(i) for i in ids)
        else:
            self.attrs.pop("characters", None)


def parse_plots(raw: bytes) -> list[Plot]:
    root = ET.fromstring(raw, _PARSER)
    plots = []
    for el in root:
        plot = Plot(attrs=dict(el.attrib))
        plot.steps = [dict(step.attrib) for step in el]
        plots.append(plot)
    return plots


def render_plots(plots: list[Plot]) -> bytes:
    root = ET.Element("root")
    for plot in plots:
        el = ET.SubElement(root, "plot")
        for k, v in _ordered(plot.attrs, PLOT_ORDER, keep_empty=False).items():
            el.attrib[k] = v
        if plot.steps:
            for step in plot.steps:
                sel = ET.SubElement(el, "step")
                for k, v in _ordered(step, STEP_ORDER, keep_empty=True).items():
                    sel.attrib[k] = v or ""
        else:
            el.attrib.pop("steps", None)
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True, pretty_print=True)


@dataclass
class WorldItem:
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["WorldItem"] = field(default_factory=list)

    @property
    def id(self) -> int:
        return int(self.attrs.get("ID", "0") or 0)

    @property
    def name(self) -> str:
        return self.attrs.get("name", "")

    def walk(self):
        for child in self.children:
            yield child
            yield from child.walk()


def _parse_world_el(el) -> WorldItem:
    return WorldItem(attrs=dict(el.attrib), children=[_parse_world_el(c) for c in el])


def parse_world(raw: bytes) -> list[WorldItem]:
    body = ET.fromstring(raw, _PARSER).find("body")
    return [] if body is None else [_parse_world_el(el) for el in body]


def _render_world_el(parent, item: WorldItem) -> None:
    el = ET.SubElement(parent, "outline")
    for k, v in _ordered(item.attrs, WORLD_ORDER, keep_empty=False).items():
        el.attrib[k] = v
    for child in item.children:
        _render_world_el(el, child)


def render_world(items: list[WorldItem]) -> bytes:
    root = ET.Element("opml")
    root.attrib["version"] = "1.0"
    body = ET.SubElement(root, "body")
    for item in items:
        _render_world_el(body, item)
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True, pretty_print=True)
