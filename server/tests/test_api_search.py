import shutil
from pathlib import Path

from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"
URL = "/api/projects/acts/search"


def setup(client, tmp_path):
    shutil.copytree(FIX, tmp_path / "projects" / "acts")
    return csrf_headers(client)


def test_finds_text_with_snippets(logged_in, tmp_path):
    setup(logged_in, tmp_path)
    r = logged_in.get(URL, params={"q": "lame man", "scope": "text"}).json()
    titles = [x["title"] for x in r["results"]]
    assert "Peter preaches" in titles and all(x["kind"] == "text" for x in r["results"])
    hit = next(x for x in r["results"] if x["title"] == "Peter preaches")
    assert hit["matches"] >= 1 and "lame man" in hit["snippets"][0].lower()


def test_case_and_whole_word(logged_in, tmp_path):
    setup(logged_in, tmp_path)
    loose = logged_in.get(URL, params={"q": "god", "scope": "text"}).json()["results"]
    exact = logged_in.get(URL, params={"q": "god", "scope": "text", "case": True}).json()["results"]
    assert sum(x["matches"] for x in loose) > sum(x["matches"] for x in exact)
    whole = logged_in.get(URL, params={"q": "Pet", "scope": "text", "word": True}).json()["results"]
    assert whole == []


def test_regex_characters_are_literal(logged_in, tmp_path):
    setup(logged_in, tmp_path)
    r = logged_in.get(URL, params={"q": "Peter.*John", "scope": "text"}).json()
    assert r["results"] == []  # as a regex this would match; literally it appears nowhere
    assert logged_in.get(URL, params={"q": "("}).status_code == 200


def test_scope_summary_notes_and_characters(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    logged_in.patch("/api/projects/acts/outline/12/fields", headers=h,
                    json={"summary_sentence": "zebra summary", "notes": "zebra note"})
    logged_in.put("/api/projects/acts/characters/0", headers=h,
                  json={"name": "Peter", "notes": "zebra friend"})
    kinds = {x["kind"] for x in logged_in.get(URL, params={"q": "zebra"}).json()["results"]}
    assert kinds == {"summary", "notes", "character"}
    only = logged_in.get(URL, params={"q": "zebra", "scope": "notes"}).json()["results"]
    assert [x["kind"] for x in only] == ["notes"]


def test_sees_edits_made_outside_the_app(logged_in, tmp_path):
    setup(logged_in, tmp_path)
    f = next((tmp_path / "projects/acts/outline").rglob("1-Peter_preaches.md"))
    f.write_text(f.read_text() + "\nquokka")
    assert logged_in.get(URL, params={"q": "quokka"}).json()["results"][0]["title"] == "Peter preaches"


def test_validation_and_auth(logged_in, tmp_path):
    setup(logged_in, tmp_path)
    assert logged_in.get(URL, params={"q": ""}).status_code == 422
    assert logged_in.get("/api/projects/nope/search", params={"q": "x"}).status_code == 404
    logged_in.cookies.clear()
    assert logged_in.get(URL, params={"q": "x"}).status_code == 401
