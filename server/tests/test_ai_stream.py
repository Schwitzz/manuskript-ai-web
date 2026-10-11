"""Chat streaming against a fake upstream model server (no network, no real model).

The fake speaks the OpenAI-style SSE that llama.cpp sends. The shapes it emits were copied
from a live run against llama.cpp (see PLAN.md Phase 4), including the reasoning_content field.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from tests.conftest import csrf_headers


def chunk(**delta):
    return "data: " + json.dumps({"choices": [{"index": 0, "delta": delta}]}) + "\n\n"


class Fake(BaseHTTPRequestHandler):
    script: list = []          # SSE strings to send, in order
    status = 200
    seen: dict = {}

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Fake.seen = body
        if Fake.status != 200:
            msg = json.dumps({"error": {"message": "model 'x' not found"}}).encode()
            self.send_response(Fake.status)
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for piece in Fake.script:
            self.wfile.write(piece.encode())
            self.wfile.flush()


@pytest.fixture()
def upstream():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    Fake.status, Fake.script, Fake.seen = 200, [], {}
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture()
def ready(logged_in, upstream):
    h = csrf_headers(logged_in)
    logged_in.post("/api/ai/providers", headers=h, json={"settings": [
        {"provider": "Local / Llama.cpp", "endpoint": upstream, "model": "m"}]})
    return logged_in, h


def run_chat(c, h, text="hi", **extra):
    req = {"project": "", "provider": "Local / Llama.cpp", "model": "m",
           "messages": [{"role": "user", "content": text}], **extra}
    with c.stream("POST", "/api/ai/chat", headers=h, json=req) as r:
        return [json.loads(ln[5:]) for ln in r.iter_lines() if ln.startswith("data:")]


def test_streams_chunks_then_a_final_event_with_the_full_text(ready):
    c, h = ready
    usage = {"choices": [], "usage": {"prompt_tokens": 9, "completion_tokens": 2}}
    Fake.script = [chunk(role="assistant", content=None), chunk(content="Hel"), chunk(content="lo"),
                   "data: " + json.dumps(usage) + "\n\n", "data: [DONE]\n\n"]
    ev = run_chat(c, h)
    assert [e["text"] for e in ev[:-1]] == ["Hel", "lo"]
    assert ev[-1]["done"] and ev[-1]["text"] == "Hello"
    assert (ev[-1]["inTokens"], ev[-1]["outTokens"]) == (9, 2)


def test_thinking_off_is_really_sent_for_local_models(ready):
    c, h = ready
    Fake.script = [chunk(content="ok"), "data: [DONE]\n\n"]
    run_chat(c, h, thinking="Off")
    assert Fake.seen["chat_template_kwargs"] == {"enable_thinking": False}
    assert Fake.seen["stream"] is True and Fake.seen["messages"][-1] == {"role": "user", "content": "hi"}
    run_chat(c, h, thinking="high")
    assert "chat_template_kwargs" not in Fake.seen and Fake.seen["reasoning_effort"] == "high"


def test_reasoning_is_streamed_apart_from_the_answer(ready):
    c, h = ready
    Fake.script = [chunk(reasoning_content="think "), chunk(reasoning_content="more"),
                   chunk(content="42"), "data: [DONE]\n\n"]
    ev = run_chat(c, h, thinking="low")
    assert [e["thinking"] for e in ev if "thinking" in e and not e.get("done")] == ["think ", "more"]
    assert ev[-1]["text"] == "42" and ev[-1]["thinking"] == "think more"


def test_a_model_that_only_thinks_gives_an_error_not_an_empty_reply(ready):
    c, h = ready
    Fake.script = [chunk(reasoning_content="hmm"), "data: [DONE]\n\n"]
    ev = run_chat(c, h)
    assert "thinking" in ev[-1]["error"].lower() and not any(e.get("done") for e in ev)


def test_empty_reply_is_an_error(ready):
    c, h = ready
    Fake.script = ["data: [DONE]\n\n"]
    assert "empty" in run_chat(c, h)[-1]["error"]


def test_upstream_error_status_is_reported_with_its_message(ready):
    c, h = ready
    Fake.status = 400
    err = run_chat(c, h)[-1]["error"]
    assert "400" in err and "not found" in err


def test_unreachable_server_is_a_clear_error(logged_in):
    h = csrf_headers(logged_in)
    logged_in.post("/api/ai/providers", headers=h, json={"settings": [
        {"provider": "Local / Llama.cpp", "endpoint": "http://127.0.0.1:1", "model": "m"}]})
    assert "connect" in run_chat(logged_in, h)[-1]["error"].lower()


def test_setup_errors_before_any_request(logged_in):
    h = csrf_headers(logged_in)
    assert "server address" in run_chat(logged_in, h)[-1]["error"]          # local, no endpoint
    assert "API key" in run_chat(logged_in, h, provider="OpenAI", model="gpt-x")[-1]["error"]
    assert "Unknown provider" in run_chat(logged_in, h, provider="Nope")[-1]["error"]
    assert "No model" in run_chat(logged_in, h, model="")[-1]["error"]


def test_chat_is_saved_only_on_success_and_with_both_messages(ready):
    c, h = ready
    cid = c.post("/api/ai/chats/new", headers=h, json={"project": "", "messages": []}).json()["chat_id"]
    Fake.script = [chunk(content="fine"), "data: [DONE]\n\n"]
    run_chat(c, h, "question", chat_id=cid)
    msgs = c.get(f"/api/ai/chats/{cid}").json()["messages"]
    assert [(m["role"], m["content"]) for m in msgs] == [("user", "question"), ("assistant", "fine")]
    Fake.status = 400
    run_chat(c, h, "again", chat_id=cid)
    assert len(c.get(f"/api/ai/chats/{cid}").json()["messages"]) == 2   # a failed turn saves nothing


def test_first_message_is_not_saved_twice_when_the_chat_was_created_with_it(ready):
    c, h = ready
    made = c.post("/api/ai/chats/new", headers=h, json={
        "project": "", "messages": [{"role": "user", "content": "hello"}]}).json()["chat_id"]
    Fake.script = [chunk(content="hi back"), "data: [DONE]\n\n"]
    run_chat(c, h, "hello", chat_id=made)
    msgs = c.get(f"/api/ai/chats/{made}").json()["messages"]
    assert [(m["role"], m["content"]) for m in msgs] == [("user", "hello"), ("assistant", "hi back")]
    # a second, different question in the same chat is added normally
    run_chat(c, h, "and again", chat_id=made)
    assert [m["role"] for m in c.get(f"/api/ai/chats/{made}").json()["messages"]] == [
        "user", "assistant", "user", "assistant"]
