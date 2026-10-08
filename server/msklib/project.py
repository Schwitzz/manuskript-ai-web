"""Read and write a Manuskript v1 project folder (plain-text format), Qt-free.

Layout on disk, for a project called `name`:
    name.msk               contains "1" (format version)
    name/MANUSKRIPT        contains "1"
    name/infos.txt  summary.txt  status.txt  labels.txt  settings.txt
    name/characters/<ID>-<slug>.txt
    name/outline/<row>-<slug>[.md]  (folders hold folder.txt)
    name/world.opml  plots.xml  revisions.xml

Round-trip rule: files are kept as decoded text; `save()` regenerates the outline
from the model and writes only files whose text differs from what was read.
Files msklib does not model (world, plots, settings, revisions) pass through untouched.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path

from msklib.model import Item

BINARY_SUFFIXES = (".xml", "opml")  # desktop reads these as bytes


def _read(path: Path) -> str | bytes:
    if path.name[-4:] in BINARY_SUFFIXES:
        return path.read_bytes()
    with open(path, "rt", encoding="utf8") as fh:
        return fh.read()


def _sort_key(name: str) -> tuple[int, str]:
    m = re.match(r"^(\d+)-", name)
    return (int(m.group(1)) if m else 10**9, name)


class Project:
    def __init__(self, root: Path):
        self.root = Path(root)  # the project folder (the one holding MANUSKRIPT)
        self.files: dict[str, str | bytes] = {}  # relative path -> content as last read/written
        self.outline = Item(id=0, title="Root", type="folder")

    @classmethod
    def load(cls, root: Path) -> "Project":
        proj = cls(root)
        for dirpath, dirnames, filenames in os.walk(proj.root):
            rel_dir = os.path.relpath(dirpath, proj.root)
            rel_dir = "" if rel_dir == "." else rel_dir
            # the desktop skips dot-directories (our .trash) and dot-files
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fn in filenames:
                if fn.startswith("."):
                    continue
                try:
                    proj.files[os.path.join(rel_dir, fn)] = _read(Path(dirpath) / fn)
                except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
                    continue
        proj._build_outline()
        return proj

    def _build_outline(self) -> None:
        prefix = "outline" + os.sep
        folders: dict[str, Item] = {"outline": self.outline}
        pending: list[tuple[str, Item]] = []  # (parent dir, item)

        # Pass 1: create every folder item, shallowest first, so parents always exist.
        folder_files = sorted((p for p in self.files if p.startswith(prefix)
                               and os.path.basename(p) == "folder.txt"),
                              key=lambda p: p.count(os.sep))
        for rel in folder_files:
            content = self.files[rel]
            if not isinstance(content, str):
                continue
            folder_dir = os.path.dirname(rel)
            item = Item.from_mmd(content, folder_dir)
            folders[folder_dir] = item
            pending.append((os.path.dirname(folder_dir), item))

        # Pass 2: scenes.
        for rel in self.files:
            content = self.files[rel]
            if (rel.startswith(prefix) and rel.endswith(".md") and isinstance(content, str)
                    and os.path.basename(rel) != "folder.txt"):
                pending.append((os.path.dirname(rel), Item.from_mmd(content, rel)))

        for parent_dir, item in pending:
            parent = folders.get(parent_dir, self.outline)
            item.parent = parent
            parent.children.append(item)
        for it in [self.outline, *self.outline.walk()]:
            it.children.sort(key=lambda c: _sort_key(os.path.basename(c.last_path)))

    # ---- saving ----

    def render_outline(self) -> dict[str, str]:
        return {item.file_path(): item.to_mmd() for item in self.outline.walk()}

    def save(self) -> list[str]:
        """Write changed outline files, move renamed ones, trash removed ones.
        Returns the relative paths written."""
        rendered = self.render_outline()
        written: list[str] = []

        # Renames / moves first (an item's path differs from where it was read).
        for item in self.outline.walk():
            new, old = item.path(), item.last_path
            if old and new != old and (self.root / old).exists() and not (self.root / new).exists():
                (self.root / new).parent.mkdir(parents=True, exist_ok=True)
                os.replace(self.root / old, self.root / new)
                for key in [k for k in self.files if k == old or k.startswith(old + os.sep)]:
                    self.files[new + key[len(old):]] = self.files.pop(key)

        for rel, content in rendered.items():
            if self.files.get(rel) != content:
                self._write(rel, content)
                written.append(rel)
        for item in self.outline.walk():
            item.last_path = item.path() if item.is_folder else item.file_path()

        # Outline files no longer in the model go to .trash, never a hard delete.
        prefix = "outline" + os.sep
        for rel in [p for p in self.files if p.startswith(prefix) and p not in rendered]:
            self._remove(rel)
        self._prune_empty_dirs()
        return written

    def _write(self, rel: str, content: str | bytes) -> None:
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".msk-")
        try:
            if isinstance(content, bytes):
                with os.fdopen(fd, "wb") as fh:
                    fh.write(content)
            else:
                with os.fdopen(fd, "wt", encoding="utf8", newline="\n") as fh:
                    fh.write(content)
            os.replace(tmp, target)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        self.files[rel] = content

    def _remove(self, rel: str) -> None:
        src = self.root / rel
        if src.exists():
            dest = self.root / ".trash" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                dest = dest.with_name(dest.name + "." + next(tempfile._get_candidate_names()))
            shutil.move(str(src), str(dest))
        self.files.pop(rel, None)

    def _prune_empty_dirs(self) -> None:
        outline = self.root / "outline"
        if not outline.is_dir():
            return
        for dirpath, _dirs, _files in os.walk(outline, topdown=False):
            if dirpath != str(outline) and not os.listdir(dirpath):
                os.rmdir(dirpath)
