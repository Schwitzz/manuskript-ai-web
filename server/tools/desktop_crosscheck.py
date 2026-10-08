"""Open a project in the real desktop Manuskript (offscreen) and save it again.

Run with the desktop fork's Python (it has PyQt5), NOT the server's venv:

    HOME=$(mktemp -d) QT_QPA_PLATFORM=offscreen \
      /home/ab/workspaces/manuskript-ai/venv/bin/python tools/desktop_crosscheck.py \
      <fork-dir> <project-dir>

<project-dir> is the folder holding MANUSKRIPT; <project-dir>.msk must sit next to it.
Prints one JSON object: what desktop loaded, and which files its own save changed.
Always point it at a COPY: the desktop save rewrites files.
"""

import hashlib
import json
import os
import sys


def snapshot(root):
    out = {}
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.startswith("."):
                continue
            p = os.path.join(dirpath, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def main():
    fork, project = sys.argv[1], os.path.abspath(sys.argv[2])
    sys.path.insert(0, fork)
    os.chdir(fork)

    from PyQt5.QtWidgets import QApplication
    QApplication([])
    from manuskript import main as msk_main
    args = msk_main.process_commandline([])
    _app, mw = msk_main.prepare(args, tests=True)
    from manuskript import functions as F
    from PyQt5.QtCore import Qt
    F.AUC = Qt.AutoConnection
    from manuskript.enums import Outline

    before = snapshot(project)
    mw.loadProject(project + ".msk")
    if mw.currentProject is None:
        print(json.dumps({"error": "desktop could not open the project"}))
        return 1

    items = []

    def walk(item):
        for child in item.children():
            items.append({"id": int(child.ID()), "title": child.title(), "type": child.type(),
                          "words": int(child.data(Outline.wordCount) or 0),
                          "chars": int(child.data(Outline.charCount) or 0),
                          "text_sha256": hashlib.sha256((child.data(Outline.text) or "").encode("utf8")).hexdigest() if child.isText() else None})
            walk(child)

    walk(mw.mdlOutline.rootItem)
    characters = [{"id": int(c.ID()), "name": c.name()} for c in mw.mdlCharacter.characters]
    result = {
        "items": items,
        "characters": characters,
        "labels": [mw.mdlLabels.item(i).text() for i in range(1, mw.mdlLabels.rowCount())],
        "status": [mw.mdlStatus.item(i).text() for i in range(1, mw.mdlStatus.rowCount())],
        "plots": mw.mdlPlots.rowCount(),
    }

    mw.saveDatas()
    after = snapshot(project)
    result["changed_by_desktop_save"] = sorted(
        k for k in set(before) | set(after) if before.get(k) != after.get(k))
    print("@@JSON@@" + json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
