"""Old scene types. Desktop Manuskript converts them to Markdown when it opens a project:
`txt` and `t2t` just become `md`; `html` becomes `md` with the markup removed.

We do the same on load. The original body stays in `Item.loaded_text`, so the next save
records it as a revision: converting never destroys the original.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre"}
SKIP_TAGS = {"script", "style", "head", "title"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip += 1
        elif tag in BLOCK_TAGS:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK_TAGS:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(html: str) -> str:
    parser = _Text()
    parser.feed(html)
    parser.close()
    text = "".join(parser.out)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    return re.sub(r"\n{2,}", "\n", text).strip("\n")


def modernise(type_: str, text: str, notes: str) -> tuple[str, str, str]:
    """(type, text, notes) as desktop would hold them after loading."""
    if type_ in ("txt", "t2t"):
        return "md", text, notes
    if type_ == "html":
        return "md", html_to_text(text), html_to_text(notes) if notes else notes
    return type_, text, notes
