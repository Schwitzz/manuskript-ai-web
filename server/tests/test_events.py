import asyncio
import json
import shutil
from pathlib import Path

import pytest

from app import events
from app.api.events import stream
from app.config import get_settings
from tests.conftest import csrf_headers

FIX = Path(__file__).parent / "fixtures" / "book-of-acts"


@pytest.fixture(autouse=True)
def clean_bus():
    events._subscribers.clear()
    events._known.clear()
    yield
    events._subscribers.clear()
    events._known.clear()


@pytest.fixture()
def projects(tmp_path, monkeypatch):
    monkeypatch.setenv("MSK_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    shutil.copytree(FIX, tmp_path / "projects" / "acts")
    yield tmp_path / "projects" / "acts"
    get_settings.cache_clear()


def test_publish_reaches_all_subscribers_and_unsubscribe_stops_it():
    async def run():
        a, b = events.subscribe(), events.subscribe()
        events.publish({"type": "changed", "project": "x"})
        assert (await a.get())["project"] == "x" and (await b.get())["project"] == "x"
        events.unsubscribe(a)
        events.publish({"type": "changed", "project": "y"})
        assert a.empty() and (await b.get())["project"] == "y"
    asyncio.run(run())


def test_a_stuck_subscriber_never_blocks_publishing():
    async def run():
        q = events.subscribe()
        for i in range(500):
            events.publish({"type": "changed", "project": str(i)})  # queue holds only 100
        assert q.qsize() == 100
    asyncio.run(run())


def test_signature_changes_on_edit_add_and_delete_but_not_on_dotfiles(projects):
    base = events.signature(projects)
    assert events.signature(projects) == base
    (projects / ".trash").mkdir()
    (projects / ".trash" / "x.md").write_text("ignored")
    (projects / ".msk-tmp").write_text("ignored")
    assert events.signature(projects) == base
    f = next((projects / "outline").rglob("1-Peter_preaches.md"))
    f.write_text(f.read_text() + "!")
    edited = events.signature(projects)
    assert edited != base
    (projects / "characters" / "9-New.txt").write_text("Name: New\nID: 9\n")
    assert events.signature(projects) != edited


def test_check_all_reports_only_real_external_changes(projects):
    assert events.check_all() == []          # first look just records the baseline
    assert events.check_all() == []          # nothing changed
    f = next((projects / "outline").rglob("1-Peter_preaches.md"))
    f.write_text(f.read_text() + "\nedited on desktop")
    assert events.check_all() == ["acts"]
    assert events.check_all() == []          # reported once


def test_watcher_publishes_external_edit_only_while_someone_listens(projects, monkeypatch):
    monkeypatch.setattr(events, "WATCH_INTERVAL", 0.05)

    async def run():
        task = asyncio.create_task(events.watcher())
        await asyncio.sleep(0.12)                       # nobody listening: nothing recorded
        assert events._known == {}
        q = events.subscribe()
        await asyncio.sleep(0.2)                        # baseline taken
        f = next((projects / "outline").rglob("1-Peter_preaches.md"))
        f.write_text(f.read_text() + "\nchanged")
        ev = await asyncio.wait_for(q.get(), timeout=2)
        task.cancel()
        return ev

    assert asyncio.run(run()) == {"type": "changed", "project": "acts", "source": "external"}


class FakeRequest:
    def __init__(self):
        self.gone = False

    async def is_disconnected(self):
        return self.gone


def test_stream_sends_hello_events_keepalive_and_cleans_up():
    async def run():
        req = FakeRequest()
        gen = stream(req, heartbeat=0.05)
        first = await gen.__anext__()
        assert "event: hello" in first and "retry: 3000" in first
        assert len(events._subscribers) == 1
        assert (await gen.__anext__()).startswith(": keepalive")
        events.publish({"type": "changed", "project": "acts", "source": "api"})
        chunk = await gen.__anext__()
        assert chunk.startswith("event: changed\ndata: ")
        assert json.loads(chunk.split("data: ", 1)[1]) == {
            "type": "changed", "project": "acts", "source": "api"}
        req.gone = True
        await gen.aclose()
        assert events._subscribers == set()
    asyncio.run(run())


def test_api_edits_publish_one_event_when_someone_listens(logged_in, tmp_path):
    shutil.copytree(FIX, tmp_path / "projects" / "acts")
    h = csrf_headers(logged_in)

    async def listen_then_edit():
        q = events.subscribe()
        await asyncio.to_thread(
            logged_in.patch, "/api/projects/acts/outline/12/title", headers=h,
            json={"title": "Peter speaks"})
        await asyncio.to_thread(logged_in.get, "/api/projects/acts/outline")  # a read: no event
        got = [q.get_nowait() for _ in range(q.qsize())]
        events.unsubscribe(q)
        return got

    got = asyncio.run(listen_then_edit())
    assert got == [{"type": "changed", "project": "acts", "source": "api"}]


def test_no_event_when_nobody_listens_and_reads_are_silent(logged_in, tmp_path):
    shutil.copytree(FIX, tmp_path / "projects" / "acts")
    logged_in.get("/api/projects/acts/outline")
    assert events._subscribers == set() and events._known == {}


def test_events_endpoint_requires_login(client):
    assert client.get("/api/events").status_code == 401
