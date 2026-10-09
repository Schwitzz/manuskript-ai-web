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

import json
import os
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

from msklib.counts import char_count
from msklib.model import Item
from msklib.revisions import Revisions, read_settings
from msklib.xmlrecords import Plot, WorldItem, parse_plots, parse_world, render_plots, render_world
from msklib.records import (Character, Label, parse_keyed, parse_labels, parse_status,
                            render_infos, render_labels, render_status, render_summary)

BINARY_SUFFIXES = (".xml", "opml")  # desktop reads these as bytes


def _read(path: Path) -> str | bytes:
    if path.name[-4:] in BINARY_SUFFIXES:
        return path.read_bytes()
    with open(path, "rt", encoding="utf8") as fh:
        return fh.read()


def _fsync_dir(path: Path) -> None:
    """Make the rename itself durable (not available on every platform)."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _sort_key(name: str) -> tuple[int, str]:
    m = re.match(r"^(\d+)-", name)
    return (int(m.group(1)) if m else 10**9, name)


class Project:
    def __init__(self, root: Path):
        self.root = Path(root)  # the project folder (the one holding MANUSKRIPT)
        self.files: dict[str, str | bytes] = {}  # relative path -> content as last read/written
        self.outline = Item(id=0, title="Root", type="folder")
        self.labels: list[Label] = []
        self.status: list[str] = []
        self.infos: dict[str, str] = {}
        self.summary: dict[str, str] = {}
        self.characters: list[Character] = []
        self.plots: list[Plot] = []
        self.world: list[WorldItem] = []
        self._xml_loaded: dict[str, bytes] = {}
        self.settings: dict = {}
        self.files_pending: dict[str, bytes] = {}  # extra files to write on the next save

    class ReadOnlyError(Exception):
        pass

    read_only = False

    @classmethod
    def load_zip(cls, path: Path) -> "Project":
        """Open a zipped project (a `.msk` file that is itself a zip, with MANUSKRIPT at its
        root). Read-only: convert it to a folder with `extract_to` to edit it."""
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            if "MANUSKRIPT" not in names:
                raise ValueError("Not a version 1 Manuskript project (no MANUSKRIPT in the zip)")
            proj = cls(Path(path))
            for name in names:
                norm = os.path.normpath(name)
                if (os.path.isabs(name) or "\\" in name
                        or any(part == ".." for part in norm.split(os.sep))):
                    raise ValueError(f"Unsafe path in archive: {name}")
                if name.endswith("/") or any(part.startswith(".") for part in norm.split(os.sep)):
                    continue
                data = zf.read(name)
                if norm[-4:] in BINARY_SUFFIXES:
                    proj.files[norm] = data
                else:
                    try:
                        proj.files[norm] = data.decode("utf8").replace("\r\n", "\n").replace("\r", "\n")
                    except UnicodeDecodeError:
                        continue
        proj.read_only = True
        proj._build_outline()
        proj._build_records()
        return proj

    def extract_to(self, dest: Path) -> "Project":
        """Write every file of this (zipped) project into a new folder and open that."""
        dest = Path(dest)
        if dest.exists():
            raise FileExistsError(str(dest))
        dest.mkdir(parents=True)
        out = Project(dest)
        for rel, content in self.files.items():
            out._write(rel, content)
        return Project.load(dest)

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
        proj._build_records()
        return proj

    def _text(self, rel: str) -> str:
        val = self.files.get(rel, "")
        return val if isinstance(val, str) else ""

    def _build_records(self) -> None:
        try:
            self.settings = json.loads(self._text("settings.txt") or "{}")
        except ValueError:
            self.settings = {}
        self.labels = parse_labels(self._text("labels.txt"))
        self.status = parse_status(self._text("status.txt"))
        self.infos = parse_keyed(self._text("infos.txt"))
        self.summary = parse_keyed(self._text("summary.txt"))
        chars = [Character.parse(self._text(p), p) for p in sorted(self.files)
                 if p.startswith("characters" + os.sep) and p.endswith(".txt")
                 and isinstance(self.files[p], str)]
        self.characters = sorted(chars, key=lambda c: c.id)
        for rel, parser, attr in (("plots.xml", parse_plots, "plots"),
                                  ("world.opml", parse_world, "world")):
            raw = self.files.get(rel)
            if isinstance(raw, bytes):
                setattr(self, attr, parser(raw))
                self._xml_loaded[rel] = raw

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
        if self.read_only:
            raise Project.ReadOnlyError("This project was opened from a zip and cannot be saved")
        self._update_char_counts()
        self._record_revisions()
        rendered = self.render_outline()
        written: list[str] = []
        records = self._render_records()

        # Renames / moves first (an item's path differs from where it was read).
        for item in self.outline.walk():
            new, old = item.path(), item.last_path
            if old and new != old and (self.root / old).exists() and not (self.root / new).exists():
                (self.root / new).parent.mkdir(parents=True, exist_ok=True)
                os.replace(self.root / old, self.root / new)
                for key in [k for k in self.files if k == old or k.startswith(old + os.sep)]:
                    self.files[new + key[len(old):]] = self.files.pop(key)

        for c in self.characters:
            old, new = c.last_path, c.path()
            if old and old != new and (self.root / old).exists() and not (self.root / new).exists():
                os.replace(self.root / old, self.root / new)
                if old in self.files:
                    self.files[new] = self.files.pop(old)

        records.update(self.files_pending)
        self.files_pending = {}
        for rel, content in {**rendered, **records}.items():
            if rel not in self.files and content in ("", b"") and rel not in rendered:
                continue  # never create an empty optional file
            if self.files.get(rel) != content:
                self._write(rel, content)
                written.append(rel)
        for item in self.outline.walk():
            item.last_path = item.path() if item.is_folder else item.file_path()
            if not item.is_folder:
                item.loaded_text = item.text

        # Outline files no longer in the model go to .trash, never a hard delete.
        prefix = "outline" + os.sep
        for rel in [p for p in self.files if p.startswith(prefix) and p not in rendered]:
            self._remove(rel)
        for rel in [p for p in self.files if p.startswith("characters" + os.sep)
                    and p.endswith(".txt") and p not in records]:
            self._remove(rel)
        for c in self.characters:
            c.last_path = c.path()
        for rel in ("plots.xml", "world.opml"):
            if isinstance(self.files.get(rel), bytes):
                self._xml_loaded[rel] = self.files[rel]
        self._prune_empty_dirs()
        return written

    def _record_revisions(self) -> None:
        """Like desktop: when a scene's text changes, keep the previous text as a revision.
        revisions.xml is only touched if something changed or an item was removed."""
        keep, smart, rules = read_settings(self._text("settings.txt"))
        if not keep:
            return
        raw = self.files.get("revisions.xml")
        revs = Revisions(raw if isinstance(raw, bytes) else None)
        now = time.time()
        for item in self.outline.walk():
            if (not item.is_folder and item.loaded_text is not None
                    and item.text != item.loaded_text):
                revs.add(item.id, item.loaded_text, now, rules, smart,
                         title=item.title, kind=item.type, path=item.file_path())
        # Desktop rebuilds revisions.xml from the live outline, so revisions of removed items go.
        live = {str(i.id) for i in self.outline.walk()} | {"0"}
        for el in list(revs.root.iter("outlineItem")):
            if el.get("ID") not in live:
                revs.drop_item(int(el.get("ID", "0") or 0))
        if revs.dirty:
            self.files_pending["revisions.xml"] = revs.tobytes()

    def _count_spaces(self) -> bool:
        try:
            return bool(json.loads(self._text("settings.txt")).get("countSpaces", True))
        except ValueError:
            return True

    def _update_char_counts(self) -> None:
        """Like desktop: write charCount (omitted when 0) for edited scenes and their parent
        folders. Untouched items keep whatever was in the file, so no needless rewrites."""
        spaces = self._count_spaces()
        dirty_folders: list[Item] = []
        for item in self.outline.walk():
            if item.is_folder:
                continue
            if item.loaded_text is not None and item.text == item.loaded_text:
                continue
            self._set_count(item, char_count(item.text, spaces))
            parent = item.parent
            while parent is not None and parent is not self.outline:
                if parent not in dirty_folders:
                    dirty_folders.append(parent)
                parent = parent.parent
        for folder in sorted(dirty_folders, key=lambda f: -len(f.path())):
            self._set_count(folder, sum(int(c.meta.get("charCount", 0) or 0)
                                        for c in folder.children))

    @staticmethod
    def _set_count(item: Item, n: int) -> None:
        if n:
            item.meta["charCount"] = str(n)
        else:
            item.meta.pop("charCount", None)

    def _render_records(self) -> dict[str, str]:
        out = {
            "labels.txt": render_labels(self.labels),
            "status.txt": render_status(self.status),
            "infos.txt": render_infos(self.infos),
            "summary.txt": render_summary(self.summary),
        }
        for c in self.characters:
            out[c.path()] = c.render()
        # settings.txt: keep the original text unless the data really changed.
        old_settings = self._text("settings.txt")
        try:
            unchanged = bool(old_settings) and json.loads(old_settings) == self.settings
        except ValueError:
            unchanged = False
        if unchanged:
            out["settings.txt"] = old_settings
        elif self.settings or old_settings:
            out["settings.txt"] = json.dumps(self.settings, indent=4, sort_keys=True)
        # XML files: only regenerate when the parsed data differs from what was read, so a
        # file written by another lxml/libxml2 version is never rewritten needlessly.
        for rel, data, render, parse in (("plots.xml", self.plots, render_plots, parse_plots),
                                         ("world.opml", self.world, render_world, parse_world)):
            old = self._xml_loaded.get(rel)
            if old is not None and render(parse(old)) == render(data):
                out[rel] = old
            elif old is None and not data:
                continue
            else:
                out[rel] = render(data)
        return out

    def _write(self, rel: str, content: str | bytes) -> None:
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".msk-")
        try:
            if isinstance(content, bytes):
                with os.fdopen(fd, "wb") as fh:
                    fh.write(content)
                    fh.flush()
                    os.fsync(fh.fileno())
            else:
                with os.fdopen(fd, "wt", encoding="utf8", newline="\n") as fh:
                    fh.write(content)
                    fh.flush()
                    os.fsync(fh.fileno())
            os.replace(tmp, target)
            _fsync_dir(target.parent)
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

    # ---- helpers for the server ----

    def next_id(self) -> int:
        """An ID not used by any outline item."""
        return max([i.id for i in self.outline.walk()] + [0]) + 1

    def find(self, item_id: int) -> Item | None:
        return next((i for i in self.outline.walk() if i.id == item_id), None)

    @classmethod
    def create(cls, root: Path, title: str, author: str = "") -> "Project":
        """Create a new blank project at `root` (a folder that must not exist yet) plus the
        `<root>.msk` marker beside it, like desktop Manuskript does."""
        root = Path(root)
        if root.exists() or root.with_name(root.name + ".msk").exists():
            raise FileExistsError(str(root))
        root.mkdir(parents=True)
        proj = cls(root)
        proj.infos = {"Title": title, **({"Author": author} if author else {})}
        proj.labels = [Label("Idea", "#ffff00"), Label("Note", "#00ff00"),
                       Label("Chapter", "#0000ff"), Label("Scene", "#ff0000"),
                       Label("Research", "#00ffff")]
        proj.status = ["TODO", "First draft", "Second draft", "Final"]
        folder = Item(id=1, title="Draft", type="folder", meta={"compile": "2"}, parent=proj.outline)
        scene = Item(id=2, title="Chapter 1", type="md", meta={"compile": "2"}, parent=folder)
        folder.children.append(scene)
        proj.outline.children.append(folder)
        proj._write("MANUSKRIPT", "1")
        proj.settings = {"viewMode": "fiction", "defaultTextType": "md", "countSpaces": True}
        proj.save()
        root.with_name(root.name + ".msk").write_text("1", encoding="utf8")
        return proj
