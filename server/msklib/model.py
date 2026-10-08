"""Outline model: folders and scenes, serialised exactly like desktop Manuskript."""

from __future__ import annotations

from dataclasses import dataclass, field

from msklib.format import format_meta, parse_mmd, slugify

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

    @property
    def is_folder(self) -> bool:
        return self.type == "folder"

    def row(self) -> int:
        return self.parent.children.index(self) if self.parent else 0

    def to_mmd(self) -> str:
        values = {"title": self.title, "ID": str(self.id), "type": self.type, **self.meta}
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
        return item

    def path(self) -> str:
        """Relative path where this item is stored (folders: the directory)."""
        if self.parent is None:
            return "outline"
        siblings = self.parent.children
        titles = [s.title for s in siblings]
        title = f"{self.title}-{self.id}" if titles.count(self.title) > 1 else self.title
        name = "{}-{}{}".format(str(self.row()).zfill(len(str(len(siblings)))), slugify(title),
                                "" if self.is_folder else ".md")
        return self.parent.path() + "/" + name

    def file_path(self) -> str:
        return self.path() + "/folder.txt" if self.is_folder else self.path()

    def walk(self):
        for child in self.children:
            yield child
            yield from child.walk()
