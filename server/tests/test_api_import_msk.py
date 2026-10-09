import io
import zipfile
from pathlib import Path

from msklib.project import Project
from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"


def desktop_zip(src: Path = FIX) -> bytes:
    """A desktop-style zipped .msk: project files at the zip root."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src.rglob("*")):
            if f.is_file():
                zf.writestr(f.relative_to(src).as_posix(), f.read_bytes())
    return buf.getvalue()


def post(client, h, data: bytes, name="Imported"):
    return client.post("/api/projects/import-msk", headers=h, params={"name": name},
                       files={"file": ("book.msk", data)})


def leftovers(tmp_path) -> list[str]:
    root = tmp_path / "projects"
    return [p.name for p in root.iterdir() if p.name.startswith(".import")] if root.exists() else []


def test_import_creates_an_editable_folder_project(logged_in, tmp_path):
    h = csrf_headers(logged_in)
    r = post(logged_in, h, desktop_zip())
    assert r.status_code == 201 and r.json() == {"name": "Imported"}
    assert (tmp_path / "projects/Imported.msk").read_text() == "1"
    assert Project.load(tmp_path / "projects/Imported").save() == []
    titles = [i["title"] for i in logged_in.get("/api/projects/Imported/outline").json()["items"]]
    assert titles[0] == "Jerusalem"
    doc = logged_in.get("/api/projects/Imported/documents/12").json()
    saved = logged_in.put("/api/projects/Imported/documents/12", headers=h,
                          json={"text": "edited", "base_version": doc["version"]})
    assert saved.status_code == 200
    assert leftovers(tmp_path) == []


def test_import_refuses_an_existing_name(logged_in, tmp_path):
    h = csrf_headers(logged_in)
    assert post(logged_in, h, desktop_zip()).status_code == 201
    assert post(logged_in, h, desktop_zip()).status_code == 409


def test_import_rejects_bad_input_and_leaves_nothing_behind(logged_in, tmp_path):
    h = csrf_headers(logged_in)
    assert post(logged_in, h, b"not a zip").status_code == 400

    old = io.BytesIO()
    with zipfile.ZipFile(old, "w") as zf:
        zf.writestr("outline.xml", "<x/>")
    assert post(logged_in, h, old.getvalue()).status_code == 400

    evil = io.BytesIO()
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("MANUSKRIPT", "1")
        zf.writestr("../escape.txt", "x")
    assert post(logged_in, h, evil.getvalue()).status_code == 400

    assert not (tmp_path / "projects/Imported").exists()
    assert not (tmp_path / "escape.txt").exists()
    assert leftovers(tmp_path) == []


def test_import_rejects_bad_names_and_needs_auth(logged_in, tmp_path):
    h = csrf_headers(logged_in)
    for bad in ("../x", ".hidden", "a/b"):
        assert post(logged_in, h, desktop_zip(), name=bad).status_code == 400, bad
    assert post(logged_in, {}, desktop_zip()).status_code == 403
    logged_in.cookies.clear()  # no session at all: refused (CSRF is checked before login)
    assert post(logged_in, {}, desktop_zip()).status_code in (401, 403)
