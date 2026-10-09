import io
import shutil
import stat
import zipfile
from pathlib import Path

from msklib.project import Project
from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"


def setup(client, tmp_path, name="acts"):
    shutil.copytree(FIX, tmp_path / "projects" / name)
    shutil.copy(FIX.parent / "book-of-acts.msk", tmp_path / "projects" / f"{name}.msk")
    return csrf_headers(client)


def make_zip(entries: dict[str, bytes], symlink: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(info, "/etc/passwd")
    return buf.getvalue()


def upload(client, h, data: bytes):
    return client.post("/api/projects/upload", headers=h, files={"file": ("p.zip", data)})


def test_rename_moves_folder_and_marker(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    r = logged_in.post("/api/projects/acts/rename", headers=h, json={"new_name": "Acts 2"})
    assert r.status_code == 200
    assert (tmp_path / "projects/Acts 2/MANUSKRIPT").exists()
    assert (tmp_path / "projects/Acts 2.msk").exists() and not (tmp_path / "projects/acts").exists()
    assert logged_in.get("/api/projects/Acts 2/outline").status_code == 200
    assert logged_in.get("/api/projects/acts/outline").status_code == 404


def test_rename_conflicts_and_bad_names(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    setup_two = shutil.copytree(FIX, tmp_path / "projects" / "other")
    assert setup_two
    assert logged_in.post("/api/projects/acts/rename", headers=h,
                          json={"new_name": "other"}).status_code == 409
    for bad in ("../x", ".hidden", "a/b"):
        assert logged_in.post("/api/projects/acts/rename", headers=h,
                              json={"new_name": bad}).status_code in (400, 422)
    assert (tmp_path / "projects/acts").exists()


def test_delete_goes_to_trash_and_can_be_recovered(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    r = logged_in.delete("/api/projects/acts", headers=h)
    assert r.status_code == 200
    trashed = tmp_path / "projects/.trash" / r.json()["trashed_as"]
    assert (trashed / "MANUSKRIPT").exists()
    assert logged_in.get("/api/projects").json()["projects"] == []
    assert Project.load(trashed).save() == []  # intact, openable


def test_download_zip_has_all_files_and_no_dotfiles(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    (tmp_path / "projects/acts/.trash").mkdir()
    (tmp_path / "projects/acts/.trash/secret.txt").write_text("x")
    r = logged_in.get("/api/projects/acts/download")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert "acts/MANUSKRIPT" in names and "acts/characters/0-Peter.txt" in names
    expected = {f"acts/{f.relative_to(FIX).as_posix()}" for f in FIX.rglob("*") if f.is_file()}
    assert set(names) == expected  # everything, and nothing from .trash


def test_download_then_upload_roundtrip(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    data = logged_in.get("/api/projects/acts/download").content
    logged_in.post("/api/projects/acts/rename", headers=h, json={"new_name": "old"})
    # the zip's top folder is "acts", so it comes back under that name
    r = upload(logged_in, h, data)
    assert r.status_code == 201 and r.json() == {"name": "acts"}
    assert Project.load(tmp_path / "projects/acts").save() == []
    assert upload(logged_in, h, data).status_code == 409  # already exists now


def test_upload_rejects_hostile_archives(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    ok = b"1"
    cases = {
        "traversal": make_zip({"p/MANUSKRIPT": ok, "p/../../evil.txt": b"x"}),
        "absolute": make_zip({"p/MANUSKRIPT": ok, "/etc/evil.txt": b"x"}),
        "two_tops": make_zip({"a/MANUSKRIPT": ok, "b/file.txt": b"x"}),
        "no_marker": make_zip({"p/readme.txt": b"x"}),
        "loose_file": make_zip({"MANUSKRIPT": ok}),
        "symlink": make_zip({"p/MANUSKRIPT": ok}, symlink="p/link"),
        "backslash": make_zip({"p/MANUSKRIPT": ok, "p\\..\\evil": b"x"}),
        "empty": make_zip({}),
    }
    for label, data in cases.items():
        assert upload(logged_in, h, data).status_code == 400, label
    assert upload(logged_in, h, b"not a zip").status_code == 400
    assert not (tmp_path / "evil.txt").exists() and not (tmp_path / "projects/evil.txt").exists()
    assert [p.name for p in (tmp_path / "projects").iterdir() if p.name.startswith(".upload")] == []


def test_upload_rejects_zip_bomb(logged_in, tmp_path, monkeypatch):
    h = setup(logged_in, tmp_path)
    from app.api import project_ops
    monkeypatch.setattr(project_ops, "MAX_UNPACKED", 1000)
    big = make_zip({"p/MANUSKRIPT": b"1", "p/big.txt": b"0" * 5000})
    assert upload(logged_in, h, big).status_code == 400


def test_upload_valid_minimal_project(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    r = upload(logged_in, h, make_zip({"fresh/MANUSKRIPT": b"1", "fresh/infos.txt": b"Title:          Fresh\n"}))
    assert r.status_code == 201
    assert any(p["name"] == "fresh" and p["title"] == "Fresh"
               for p in logged_in.get("/api/projects").json()["projects"])


def test_ops_need_login_and_csrf(logged_in, tmp_path):
    setup(logged_in, tmp_path)
    assert logged_in.delete("/api/projects/acts").status_code == 403
    assert logged_in.post("/api/projects/acts/rename", json={"new_name": "z"}).status_code == 403
    logged_in.cookies.clear()
    assert logged_in.get("/api/projects/acts/download").status_code == 401
