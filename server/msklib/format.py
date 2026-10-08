"""Low-level helpers for Manuskript's plain-text (MultiMarkdown-style) files.

Ported from manuskript/load_save/version_1.py without any Qt dependency.
"""

import re
import string
from collections import OrderedDict


def slugify(name: str) -> str:
    """Spaces/whitespace become '_', anything not ASCII letter/digit becomes '-'."""
    valid = string.ascii_letters + string.digits
    out = []
    for c in name:
        if c in valid:
            out.append(c)
        elif c in string.whitespace:
            out.append("_")
        else:
            out.append("-")
    return "".join(out)


def format_meta(name: str, value: str, tab: int = 10) -> str:
    """One 'Name:   value' line, with multi-line values indented under the first line."""
    if len(value.split("\n")) > 1:
        value = "\n".join([" " * (tab + 1) + ln for ln in value.split("\n")])[tab + 1:]
    if name == "":
        name = "None"
    name = name.replace(":", "_.._")
    return "{name}:{spaces}{value}\n".format(name=name, spaces=" " * (tab - len(name)), value=value)


def clean_value(value: str) -> str:
    """A header value as it will read back: the parser drops blanks after the colon and
    strips continuation lines. Use it before writing so the first save is already stable."""
    first, *rest = value.split("\n")
    return "\n".join([first.lstrip(), *[ln.strip() for ln in rest]])


_META_RE = re.compile(r"^([^\s].*?):\s*(.*)$")


def parse_mmd_pairs(text: str) -> tuple[list[tuple[str, str]], str]:
    """Split a file into (ordered [(key, value)] pairs, body). Keeps repeated keys,
    like the desktop's parseMMDFile(asDict=False)."""
    pairs: list[tuple[str, str]] = []
    body: list[str] = []
    descr = ""
    val = ""
    in_body = False

    def commit():
        if descr:
            pairs.append(("" if descr == "None" else descr, val))

    for line in text.split("\n"):
        if not in_body:
            m = _META_RE.match(line)
            if m:
                commit()
                descr, val = m.group(1), m.group(2)
            elif line[:4] == "    ":
                val += "\n" + line.strip()
            elif line == "":
                in_body = True
                commit()
        else:
            body.append(line)

    if body and body[0] == "":
        body = body[1:]
    return pairs, "\n".join(body)


def parse_mmd(text: str) -> tuple["OrderedDict[str, str]", str]:
    """Like parse_mmd_pairs, but metadata as a dict (last duplicate wins)."""
    pairs, body = parse_mmd_pairs(text)
    return OrderedDict(pairs), body
