from pathlib import Path

from msklib.counts import char_count, item_counts, word_count
from msklib.project import Project

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"


def test_word_count_rules():
    assert word_count("") == 0
    assert word_count("one two\nthree\tfour") == 4
    assert word_count("a <!-- hidden words here --> b") == 2
    assert word_count("a <!-- multi\nline --> b") == 2
    assert word_count("x\u00a0y") == 2  # no-break space separates words, like desktop


def test_char_count_rules():
    assert char_count("ab cd") == 5
    assert char_count("ab cd", use_spaces=False) == 4
    assert char_count("ab\ncd\te") == 5  # newline and tab are not counted
    assert char_count("a\u00a0b") == 2  # no-break space is not counted


def test_folder_counts_sum_children():
    p = Project.load(FIX)
    chapter = next(i for i in p.outline.walk() if i.title == "Chapter 2")
    words, chars = item_counts(chapter)
    assert words == sum(word_count(c.text) for c in chapter.walk() if not c.is_folder)
    assert words > 100 and chars > words
    root_words, _ = item_counts(p.outline)
    assert root_words > words
