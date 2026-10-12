"""The AI routes as the web app's store calls them (web/src/lib/stores/ai.svelte.ts)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from tests.conftest import csrf_headers


def test_providers_roundtrip_never_returns_the_key(logged_in):
    h = csrf_headers(logged_in)
    first = logged_in.get("/api/ai/providers").json()["settings"]
    assert [s["provider"] for s in first] == ["Local / Llama.cpp", "OpenAI", "Anthropic", "Google Gemini"]
    assert not any(s["has_key"] for s in first)

    body = {"settings": [{"provider": "OpenAI", "api_key": "sk-SECRET-123", "model": "gpt-x"}]}
    r = logged_in.post("/api/ai/providers", headers=h, json=body)
    assert r.status_code == 200 and "sk-SECRET-123" not in r.text
    openai = next(s for s in r.json()["settings"] if s["provider"] == "OpenAI")
    assert openai["has_key"] is True and openai["api_key"] == "" and openai["model"] == "gpt-x"
    assert "sk-SECRET-123" not in logged_in.get("/api/ai/providers").text

    # saving the form again with a blank key keeps the saved one
    again = {"settings": [{"provider": "OpenAI", "api_key": "", "model": "gpt-y"}]}
    r = logged_in.post("/api/ai/providers", headers=h, json=again).json()["settings"]
    assert next(s for s in r if s["provider"] == "OpenAI")["has_key"] is True


def test_unknown_provider_is_rejected(logged_in):
    h = csrf_headers(logged_in)
    r = logged_in.post("/api/ai/providers", headers=h, json={"settings": [{"provider": "Nope"}]})
    assert r.status_code == 422
    assert logged_in.get("/api/ai/models", params={"provider": "Nope"}).status_code == 422


def test_agent_prompt_edit_is_saved_and_used(logged_in, tmp_path):
    h = csrf_headers(logged_in)
    agents = logged_in.get("/api/ai/agents").json()["agents"]
    name = agents[0]["name"]
    r = logged_in.put("/api/ai/agents", headers=h, json={"name": name, "prompt": "Be terse."})
    assert r.status_code == 200
    assert next(a for a in r.json()["agents"] if a["name"] == name)["prompt"] == "Be terse."
    assert len(r.json()["agents"]) == len(agents)  # the other agents are untouched
    from app.ai.routes import _agent_prompt
    assert _agent_prompt(name) == "Be terse."
    assert logged_in.put("/api/ai/agents", headers=h, json={"name": "Nobody", "prompt": "x"}).status_code == 422


def test_new_chat_list_rename_delete(logged_in):
    h = csrf_headers(logged_in)
    made = logged_in.post("/api/ai/chats/new", headers=h, json={"project": "novel", "messages": []})
    assert made.status_code == 200
    cid = made.json()["chat_id"]
    chats = logged_in.get("/api/ai/chats").json()["chats"]
    assert [c["id"] for c in chats] == [cid] and chats[0]["project"] == "novel"
    assert logged_in.put(f"/api/ai/chats/{cid}", headers=h, json={"title": "Plot ideas"}).status_code == 200
    assert logged_in.get(f"/api/ai/chats/{cid}").json()["title"] == "Plot ideas"
    assert logged_in.delete(f"/api/ai/chats/{cid}", headers=h).status_code == 200
    assert logged_in.get(f"/api/ai/chats/{cid}").status_code == 404


def test_models_are_cached_per_provider(logged_in, tmp_path):
    # seed the cache for two providers; each must answer from its own entry
    import time
    cache = {"OpenAI|": {"ts": time.time(), "models": ["gpt-a"]},
             "Anthropic|": {"ts": time.time(), "models": ["claude-a"]}}
    (tmp_path / "app" / "ai").mkdir(parents=True, exist_ok=True)
    (tmp_path / "app" / "ai" / "ai_models_cache.json").write_text(json.dumps(cache))
    assert logged_in.get("/api/ai/models", params={"provider": "OpenAI"}).json() == {"models": ["gpt-a"]}
    assert logged_in.get("/api/ai/models", params={"provider": "Anthropic"}).json() == {"models": ["claude-a"]}


def test_models_are_fetched_from_the_saved_address_never_from_the_request(logged_in, upstream_models):
    h = csrf_headers(logged_in)
    logged_in.post("/api/ai/providers", headers=h, json={"settings": [
        {"provider": "Local / Llama.cpp", "endpoint": upstream_models.url, "model": "a"}]})
    # a caller-supplied endpoint is ignored: it must not make the server fetch another address
    r = logged_in.get("/api/ai/models", params={"provider": "Local / Llama.cpp",
                                               "endpoint": "http://127.0.0.1:1"})
    assert r.status_code == 200 and r.json() == {"models": ["alpha", "beta"]}
    assert upstream_models.hits == 1


def test_models_errors_are_readable(logged_in):
    h = csrf_headers(logged_in)
    r = logged_in.get("/api/ai/models", params={"provider": "Local / Llama.cpp"})
    assert r.status_code == 422 and "server address" in r.json()["detail"]
    logged_in.post("/api/ai/providers", headers=h, json={"settings": [
        {"provider": "Local / Llama.cpp", "endpoint": "http://127.0.0.1:1", "model": "a"}]})
    r = logged_in.get("/api/ai/models", params={"provider": "Local / Llama.cpp"})
    assert r.status_code == 422 and "Could not reach" in r.json()["detail"]


@pytest.fixture()
def upstream_models():
    state = SimpleNamespace(hits=0, url="")

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            state.hits += 1
            body = json.dumps({"data": [{"id": "beta"}, {"id": "alpha"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    state.url = f"http://127.0.0.1:{srv.server_port}"
    yield state
    srv.shutdown()


def test_ai_data_lives_under_app_data_so_it_is_on_the_mounted_volume(logged_in, tmp_path):
    """In Docker only data/app and data/projects are volumes and only they are writable by the
    app user. AI files written to the data root crashed the first save (PermissionError)."""
    h = csrf_headers(logged_in)
    logged_in.post("/api/ai/providers", headers=h, json={"settings": [
        {"provider": "OpenAI", "api_key": "sk-x", "model": "m"}]})
    logged_in.put("/api/ai/agents", headers=h, json={"name": "Editor", "prompt": "p"})
    logged_in.post("/api/ai/chats/new", headers=h, json={"project": "", "messages": []})
    assert (tmp_path / "app" / "ai" / "ai_providers.json").is_file()
    assert (tmp_path / "app" / "ai" / "ai_agents.json").is_file()
    assert (tmp_path / "app" / "ai" / "chats" / "chats.db").is_file()
    strays = [p.name for p in tmp_path.iterdir() if p.name not in ("app", "projects", "templates")]
    assert strays == [], f"files written outside the mounted folders: {strays}"


def test_files_from_an_older_version_are_moved_not_lost(client, tmp_path):
    (tmp_path / "ai_providers.json").write_text(json.dumps({"OpenAI": {"api_key": "sk-old", "model": "m"}}))
    from app.ai.history import ChatStore
    old_store = ChatStore(str(tmp_path / "ai_chats"))  # a real history, as the old version wrote it
    old_store.save({"id": "c1", "title": "Old chat", "project": "p", "messages": [{"role": "user", "content": "hi"}]})
    old_store.close()
    client.post("/api/auth/setup", json={"username": "ab", "password": "correct horse battery"})
    got = {s["provider"]: s for s in client.get("/api/ai/providers").json()["settings"]}
    assert got["OpenAI"]["has_key"] is True and got["OpenAI"]["model"] == "m"
    assert not (tmp_path / "ai_providers.json").exists()
    assert (tmp_path / "app" / "ai" / "ai_providers.json").is_file()
    chats = client.get("/api/ai/chats").json()["chats"]
    assert [c["title"] for c in chats] == ["Old chat"]          # the history survived the move
    assert not (tmp_path / "ai_chats").exists()
