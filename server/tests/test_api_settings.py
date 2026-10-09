import json
import shutil
from pathlib import Path

from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"
URL = "/api/projects/acts/settings"


def setup(client, tmp_path):
    shutil.copytree(FIX, tmp_path / "projects" / "acts")
    return csrf_headers(client)


def on_disk(tmp_path):
    return json.loads((tmp_path / "projects/acts/settings.txt").read_text())


def test_get_has_defaults_and_values(logged_in, tmp_path):
    setup(logged_in, tmp_path)
    s = logged_in.get(URL).json()
    assert s["viewMode"] == "fiction" and s["dict"] == "en_US" and s["revisions"]["keep"] is True
    assert s["revisions"]["rules"]["null"] == 604800


def test_patch_changes_only_what_was_sent_and_keeps_desktop_state(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    before = on_disk(tmp_path)
    r = logged_in.patch(URL, headers=h, json={"countSpaces": False, "revisions": {"keep": False}})
    assert r.status_code == 200
    after = on_disk(tmp_path)
    assert after["countSpaces"] is False and after["revisions"]["keep"] is False
    assert after["revisions"]["rules"] == before["revisions"]["rules"]  # untouched
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    assert changed == {"countSpaces", "revisions"}  # window, fonts, columns all preserved


def test_settings_file_format_is_what_desktop_writes(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    logged_in.patch(URL, headers=h, json={"dict": "en_GB"})
    text = (tmp_path / "projects/acts/settings.txt").read_text()
    assert text == json.dumps(json.loads(text), indent=4, sort_keys=True)
    from msklib.project import Project
    assert Project.load(tmp_path / "projects/acts").save() == []


def test_a_no_op_patch_does_not_rewrite_the_file(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    f = tmp_path / "projects/acts/settings.txt"
    f.write_text(f.read_text())  # normalise
    before = f.stat().st_mtime_ns
    logged_in.patch(URL, headers=h, json={"viewMode": "fiction"})
    assert f.stat().st_mtime_ns == before


def test_count_spaces_setting_changes_char_counts(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    logged_in.patch(URL, headers=h, json={"countSpaces": False})
    doc = logged_in.get("/api/projects/acts/documents/12").json()
    logged_in.put("/api/projects/acts/documents/12", headers=h,
                  json={"text": "ab cd", "base_version": doc["version"]})
    scene = next((tmp_path / "projects/acts/outline").rglob("1-Peter_preaches.md")).read_text()
    assert "charCount:      4" in scene  # the space is not counted


def test_invalid_values_are_rejected(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    for bad in ({"viewMode": "weird"}, {"dict": "../../x"}, {"countSpaces": "maybe"},
                {"defaultTextType": "html"}):
        assert logged_in.patch(URL, headers=h, json=bad).status_code == 422, bad
    assert on_disk(tmp_path) == json.loads((FIX / "settings.txt").read_text())


def test_unknown_keys_are_ignored_not_written(logged_in, tmp_path):
    h = setup(logged_in, tmp_path)
    logged_in.patch(URL, headers=h, json={"autoSave": True, "evil": 1})
    assert on_disk(tmp_path) == json.loads((FIX / "settings.txt").read_text())


def test_auth(logged_in, tmp_path):
    setup(logged_in, tmp_path)
    assert logged_in.patch(URL, json={"countSpaces": False}).status_code == 403
    logged_in.cookies.clear()
    assert logged_in.get(URL).status_code == 401
