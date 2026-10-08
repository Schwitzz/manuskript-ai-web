"""Typed records for the small project files, with the desktop's exact write rules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from msklib.format import clean_value, format_meta, parse_mmd, parse_mmd_pairs, slugify

# Desktop characterMap: (attribute, file key) in write order.
CHARACTER_FIELDS = [
    ("name", "Name"), ("id", "ID"), ("importance", "Importance"), ("pov", "POV"),
    ("motivation", "Motivation"), ("goal", "Goal"), ("conflict", "Conflict"),
    ("epiphany", "Epiphany"), ("summary_sentence", "Phrase Summary"),
    ("summary_para", "Paragraph Summary"), ("summary_full", "Full Summary"),
    ("notes", "Notes"),
]
_BY_KEY = {key: attr for attr, key in CHARACTER_FIELDS}


@dataclass
class Character:
    id: int
    name: str = ""
    importance: str = "0"
    pov: str = ""
    motivation: str = ""
    goal: str = ""
    conflict: str = ""
    epiphany: str = ""
    summary_sentence: str = ""
    summary_para: str = ""
    summary_full: str = ""
    notes: str = ""
    color: str = "#000000"
    infos: list[tuple[str, str]] = field(default_factory=list)
    last_path: str = ""

    def path(self) -> str:
        return "characters/{}-{}.txt".format(self.id, slugify(clean_value(self.name).strip()))

    def render(self) -> str:
        values = {**self.__dict__, "id": str(self.id)}
        out = ""
        for attr, key in CHARACTER_FIELDS:
            val = clean_value(str(values[attr]).strip())
            if val:
                out += format_meta(key, val, 20)
        out += format_meta("Color", clean_value(self.color), 20)
        for desc, val in self.infos:
            out += format_meta(desc.strip(), clean_value(val), 20)
        return out

    @classmethod
    def parse(cls, text: str, path: str) -> "Character":
        pairs, _body = parse_mmd_pairs(text)
        c = cls(id=0, last_path=path)
        seen_color = False
        for desc, val in pairs:
            if desc in _BY_KEY:
                attr = _BY_KEY[desc]
                setattr(c, attr, int(val or 0) if attr == "id" else val)
            elif desc == "Color" and not seen_color:
                c.color = val
                seen_color = True
            else:
                c.infos.append((desc, val))
        return c


@dataclass
class Label:
    name: str
    color: str = ""


def render_labels(labels: list[Label]) -> str:
    out = ""
    for lb in labels:
        if lb.name:
            out += "{}{}\n".format(
                lb.name, "" if not lb.color else ":" + " " * (20 - len(lb.name)) + lb.color)
    return out


def parse_labels(text: str) -> list[Label]:
    labels = []
    for line in text.split("\n"):
        if not line:
            continue
        m = re.search(r"^(.*?):\s*(.*)$", line)
        labels.append(Label(m.group(1), m.group(2)) if m else Label(line))
    return labels


def render_status(items: list[str]) -> str:
    return "".join(s + "\n" for s in items if s)


def parse_status(text: str) -> list[str]:
    return [s for s in text.split("\n") if s]


INFO_KEYS = ["Title", "Subtitle", "Serie", "Volume", "Genre", "License", "Author", "Email"]
SUMMARY_KEYS = ["Situation", "Sentence", "Paragraph", "Page", "Full"]


def render_infos(info: dict[str, str]) -> str:
    out = ""
    for key in INFO_KEYS:
        val = info.get(key, "").strip()
        if val:
            out += "{}:{}{}\n".format(key, " " * (15 - len(key)), val)
    for key, val in info.items():  # keep keys this version does not know
        if key not in INFO_KEYS and val.strip():
            out += format_meta(key, val.strip(), 15)
    return out


def render_summary(summary: dict[str, str]) -> str:
    out = ""
    for key in SUMMARY_KEYS:
        val = summary.get(key, "").strip()
        if val:
            out += format_meta(key, val, 12)
    return out


def parse_keyed(text: str) -> dict[str, str]:
    meta, _body = parse_mmd(text)
    return dict(meta)
