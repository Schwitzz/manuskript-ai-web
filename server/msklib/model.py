"""Outline model: folders and scenes, serialised exactly like desktop Manuskript."""

from __future__ import annotations

from dataclasses import dataclass, field

from msklib.format import clean_value, format_meta, parse_mmd, slugify

# Order of the metadata keys in a file (the desktop Outline enum order).
# title/ID/type are always written, `compile` is written even when empty.
META_ORDER = ["title", "ID", "type", "summarySentence", "summaryFull", "POV", "notes",
              "label", "status", "compile", "setGoal", "textFormat", "customIcon", "charCount"]
ALWAYS = {"title", "ID", "type", "compile"}


@dataclass
class Item:
    id: int
    title: str = ""
    type: str = "md"  # "folder" or "md"
    meta: dict[str, str] = field(default_factory=dict)  # every other key, as strings
    text: str = ""
    children: list["Item"] = field(default_factory=list)
    parent: "Item | None" = field(default=None, repr=False)
    last_path: str = ""  # where it was read from / last written
    loaded_text: str | None = None  # text as read, to detect edits
    _names: dict[int, str] | None = field(default=None, repr=False, compare=False)

    @property
    def is_folder(self) -> bool:
        return self.type == "folder"

    def row(self) -> int:
        return self.parent.children.index(self) if self.parent else 0

    def to_mmd(self) -> str:
        values = {"title": self.title, "ID": str(self.id), "type": self.type, **self.meta}
        values = {k: clean_value(str(v)) for k, v in values.items()}
        out = ""
        for key in META_ORDER:
            val = values.get(key, "")
            if val or key in ALWAYS:
                out += format_meta(key, str(val), 15)
        # keys this version does not know about are kept, after the known ones
        for key, val in values.items():
            if key not in META_ORDER and val:
                out += format_meta(key, str(val), 15)
        return out + "\n\n" + self.text

    @classmethod
    def from_mmd(cls, content: str, path: str) -> "Item":
        meta, body = parse_mmd(content)
        meta = dict(meta)
        item = cls(
            id=int(meta.pop("ID", "0") or 0),
            title=meta.pop("title", ""),
            type=meta.pop("type", "md"),
            text=body,
            last_path=path,
        )
        item.meta = meta
        item.loaded_text = body
        return item

    def path(self) -> str:
        """Relative path where this item is stored (folders: the directory)."""
        if self.parent is None:
            return "outline"
        return self.parent.path() + "/" + self.parent.child_names()[id(self)]

    def child_names(self) -> dict[int, str]:
        """Names of all children, cached until `forget_names()` (Project.save does that).
        Without the cache every item recomputed all of its siblings: quadratic per folder."""
        if self._names is None:
            self._names = self._child_names()
        return self._names

    def forget_names(self) -> None:
        self._names = None

    def _child_names(self) -> dict[int, str]:
        """File/folder name of every child, computed once per parent (linear, not quadratic)."""
        cleaned = [clean_value(c.title) for c in self.children]
        counts: dict[str, int] = {}
        for t in cleaned:
            counts[t] = counts.get(t, 0) + 1
        width = len(str(len(self.children)))
        names = {}
        for row, (child, title) in enumerate(zip(self.children, cleaned)):
            if counts[title] > 1:
                title = f"{title}-{child.id}"
            names[id(child)] = "{}-{}{}".format(str(row).zfill(width), slugify(title),
                                               "" if child.is_folder else ".md")
        return names

    def file_path(self) -> str:
        return self.path() + "/folder.txt" if self.is_folder else self.path()

    def walk(self):
        for child in self.children:
            yield child
            yield from child.walk()
