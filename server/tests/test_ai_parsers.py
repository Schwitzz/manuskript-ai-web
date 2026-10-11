"""Stream parsers and request payloads for the four providers (pure functions, no server)."""

import json

from app.ai import ANTHROPIC, GEMINI, LOCAL, OPENAI, buildPayload, parseStreamLine


def line(obj):
    return "data: " + json.dumps(obj)


def test_parse_openai_and_local_text_usage_done():
    for prov in (OPENAI, LOCAL):
        assert parseStreamLine(prov, line({"choices": [{"delta": {"content": "x"}}]})).text == "x"
        ev = parseStreamLine(prov, line({"choices": [], "usage": {"prompt_tokens": 3, "completion_tokens": 4}}))
        assert (ev.inTokens, ev.outTokens) == (3, 4)
        assert parseStreamLine(prov, "data: [DONE]").done
        assert parseStreamLine(prov, "") is None and parseStreamLine(prov, ": keep-alive") is None
        assert parseStreamLine(prov, "data: {not json") is None
        assert parseStreamLine(prov, line({"error": {"message": "bad key"}})).error == "bad key"


def test_parse_reasoning_content_and_bytes_input():
    ev = parseStreamLine(LOCAL, line({"choices": [{"delta": {"reasoning_content": "hm"}}]}).encode())
    assert ev.thinking == "hm" and ev.text == ""


def test_parse_anthropic():
    d = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hi"}}
    assert parseStreamLine(ANTHROPIC, line(d)).text == "hi"
    t = {"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "ponder"}}
    assert parseStreamLine(ANTHROPIC, line(t)).thinking == "ponder"
    start = {"type": "message_start", "message": {"usage": {"input_tokens": 7}}}
    assert parseStreamLine(ANTHROPIC, line(start)).inTokens == 7
    assert parseStreamLine(ANTHROPIC, line({"type": "message_delta", "usage": {"output_tokens": 5}})).outTokens == 5
    assert parseStreamLine(ANTHROPIC, line({"type": "message_stop"})).done
    assert parseStreamLine(ANTHROPIC, line({"type": "ping"})) is None


def test_parse_gemini_text_thought_and_usage():
    d = {"candidates": [{"content": {"parts": [{"text": "plan", "thought": True}, {"text": "answer"}]}}],
         "usageMetadata": {"promptTokenCount": 2, "candidatesTokenCount": 3}}
    ev = parseStreamLine(GEMINI, line(d))
    assert ev.text == "answer" and ev.thinking == "plan" and (ev.inTokens, ev.outTokens) == (2, 3)


def test_payloads_per_provider():
    hist = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a", "agent": "x"}]
    a = buildPayload(ANTHROPIC, "claude", "SYS", hist)
    assert a["system"] == "SYS" and a["stream"]
    assert a["messages"] == [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
    g = buildPayload(GEMINI, "gem", "SYS", hist)
    assert g["systemInstruction"]["parts"][0]["text"] == "SYS"
    assert [c["role"] for c in g["contents"]] == ["user", "model"]
    o = buildPayload(OPENAI, "gpt", "SYS", hist, temperature=0.2)
    assert o["messages"][0] == {"role": "system", "content": "SYS"} and o["temperature"] == 0.2
    assert "chat_template_kwargs" not in o and "max_tokens" not in o   # local-only options
