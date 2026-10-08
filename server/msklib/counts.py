"""Word and character counts, identical to desktop Manuskript (manuskript/functions)."""

import re

from msklib.model import Item

_COMMENT = re.compile(r"(<!--).+?(-->)", flags=re.DOTALL)


def word_count(text: str) -> int:
    """Whitespace-separated words, ignoring HTML comments."""
    return len(re.findall(r"\S+", _COMMENT.sub("", text)))


def char_count(text: str, use_spaces: bool = True) -> int:
    """Characters, counting plain spaces only when use_spaces is true.
    Newlines, tabs and no-break spaces are never counted (same as desktop)."""
    return len(re.findall(r"[\S ]" if use_spaces else r"\S", text))


def item_counts(item: Item, use_spaces: bool = True) -> tuple[int, int]:
    """(words, chars) for a scene, or the sum over everything inside a folder."""
    if item.is_folder:
        words = chars = 0
        for child in item.children:
            w, c = item_counts(child, use_spaces)
            words += w
            chars += c
        return words, chars
    return word_count(item.text), char_count(item.text, use_spaces)
