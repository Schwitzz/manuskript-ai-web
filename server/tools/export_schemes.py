"""Export the desktop Manuskript colour schemes (Qt-free) as JSON for the web app.

    python tools/export_schemes.py <path-to-desktop>/manuskript/appearance > ../web/src/lib/themes/schemes.json

Loads schemes.py and colors.py straight from their files, so no Qt and no desktop install
are needed. The output has the contrast-adjusted base colours AND the derived colours, which
the web app's TypeScript colour maths is tested against.
"""

import importlib.util
import json
import sys
import types
from pathlib import Path


def load(appearance: Path):
    pkg = types.ModuleType("manuskript")
    pkg.__path__ = []
    sub = types.ModuleType("manuskript.appearance")
    sub.__path__ = []
    sys.modules["manuskript"], sys.modules["manuskript.appearance"] = pkg, sub
    out = {}
    for name in ("colors", "schemes"):
        spec = importlib.util.spec_from_file_location(f"manuskript.appearance.{name}",
                                                      appearance / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        setattr(sub, name, mod)
        spec.loader.exec_module(mod)
        out[name] = mod
    return out["colors"], out["schemes"]


def main():
    colors, schemes = load(Path(sys.argv[1]))
    items = []
    for s in schemes.SCHEMES.values():
        items.append({
            "id": s.id, "name": s.name, "dark": s.dark,
            "window": s.window, "panel": s.panel, "editor": s.editor, "text": s.text,
            "muted": s.muted, "accent": s.accent, "success": s.success,
            "warning": s.warning, "error": s.error,
            "derived": schemes.derived(s),
            "derivedRedAccent": schemes.derived(s, accent="#ff0000"),
        })
    json.dump({"default": schemes.DEFAULT, "schemes": items}, sys.stdout, indent=1, ensure_ascii=False)
    sys.stdout.write("\n")


main()
