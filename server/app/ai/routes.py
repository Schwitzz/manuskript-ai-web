"""AI assistant API: chat streaming, model list, provider settings, history."""

import json
import logging
import time
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import projects as store
from app.ai import (
    LOCAL, PROVIDERS, OPENAI, ANTHROPIC, GEMINI,
    ANTHROPIC_MAX_TOKENS, THINKING_LEVELS,
    buildPayload, chatUrl, estimateTokens, headers,
    modelsUrl, parseModels, parseStreamLine,
)
from app.ai import context
from app.ai.history import ChatStore
from app.auth.deps import current_user
from app.config import get_settings

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ProviderSetting(BaseModel):
    provider: str
    api_key: str = ""  # write-only; never echoed back
    model: str = ""
    endpoint: str = ""  # only for local provider
    context_size: int = 4096
    temperature: float = 0.7
    thinking: str = "Off"  # only for local provider
    has_key: bool = False  # read-only: tells the UI a key is saved without revealing it

    model_config = {"arbitrary_types_allowed": True}


class ChatRequest(BaseModel):
    project: str = ""
    scene_id: int | None = None  # the scene open in the editor, for scene/summary/POV context
    chat_id: str | None = None  # None = new chat
    messages: list[dict] = []  # {role, content}
    provider: str = OPENAI
    model: str = ""
    agent: str = "Co-author"  # role/prompt key
    temperature: float = 0.7
    thinking: str = "Off"  # for local provider

    context_sources: dict[str, bool] = {
        "selection": True, "scene": True,
        "summary": True, "pov": True, "book": True,
    }
    context_max_tokens: int = 2000


class NewChatResponse(BaseModel):
    ok: bool
    chat_id: str


class ChatListEntry(BaseModel):
    id: str
    title: str
    project: str
    created: float
    updated: float


class ChatListResponse(BaseModel):
    chats: list[ChatListEntry]


class HistoryMessage(BaseModel):
    role: str
    content: str
    agent: str | None = None


class HistoryResponse(BaseModel):
    id: str
    title: str
    project: str
    created: float
    updated: float
    messages: list[HistoryMessage]


class ModelsResponse(BaseModel):
    models: list[str]


class AgentPrompt(BaseModel):
    name: str
    prompt: str


class AgentPromptsResponse(BaseModel):
    agents: list[AgentPrompt]


class RenameChatRequest(BaseModel):
    title: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PROMPTS = {
    "Co-author": (
        "You are a creative co-author. Continue the narrative naturally, "
        "matching the author's voice and style. Do not change the direction "
        "of the story without being asked."
    ),
    "Editor": (
        "You are a developmental editor. Suggest improvements to the text: "
        "structure, pacing, clarity, and character consistency. Be specific "
        "and provide examples."
    ),
    "Publisher": (
        "You are an experienced literary agent and book publisher. Evaluate "
        "this manuscript from a market perspective: hook, genre fit, "
        "reader appeal, and commercial viability."
    ),
    "Reader": (
        "You are a careful reader. Summarize what you understood, note any "
        "confusing passages, and describe your emotional response to the text."
    ),
}


def _saved_prompts() -> dict:
    path = _ai_file("ai_agents.json")
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if k in DEFAULT_PROMPTS and isinstance(v, str)}


def _agent_prompt(agent: str) -> str:
    """System prompt for an agent: the user's saved edit if any, else the built-in one."""
    name = agent if agent in DEFAULT_PROMPTS else "Co-author"
    return _saved_prompts().get(name, DEFAULT_PROMPTS[name])


# ---------------------------------------------------------------------------
# Route: provider settings
# ---------------------------------------------------------------------------

log = logging.getLogger(__name__)

_LEGACY = {"ai_agents.json": "ai_agents.json", "ai_providers.json": "ai_providers.json",
           "ai_models_cache.json": "ai_models_cache.json", "chats": "ai_chats"}


def _ai_file(name: str) -> Path:
    """Path of an AI data file inside the app data folder, creating the folder on first use.
    Files an earlier version wrote to the data root are moved in once, so nothing is lost."""
    conf = get_settings()
    conf.ai_dir.mkdir(parents=True, exist_ok=True)
    target = conf.ai_dir / name
    old = conf.data_dir / _LEGACY.get(name, name)
    if old.exists() and not target.exists():
        try:
            old.rename(target)
        except OSError:
            pass  # read-only or another device: leave it, the app just starts fresh
    return target


router = APIRouter(prefix="/api/ai", tags=["ai"], dependencies=[Depends(current_user)])


def _masked(provider: str, data: dict) -> ProviderSetting:
    """Saved settings for the UI: the key itself is never sent back, only whether one is set."""
    saved = dict(data.get(provider, {}))
    has_key = bool(saved.get("api_key"))
    saved["api_key"] = ""
    ps = ProviderSetting(**{"provider": provider, **saved})
    ps.has_key = has_key
    return ps


class ProvidersBody(BaseModel):
    settings: list[ProviderSetting]


@router.get("/providers", response_model=ProvidersBody)
def get_providers():
    """Return provider settings for the current project."""
    settings = get_settings()
    project_settings_path = _ai_file("ai_providers.json")
    data = {}
    if project_settings_path.is_file():
        try:
            with open(project_settings_path, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    return {"settings": [_masked(p, data) for p in PROVIDERS]}


@router.post("/providers", response_model=ProvidersBody)
def update_providers(body: ProvidersBody):
    """Update provider settings. An empty api_key means "keep the saved key" (the form never
    shows keys, so it cannot send them back). Keys are stored as plain text in the data folder."""
    settings_in = body.settings
    settings = get_settings()
    project_settings_path = _ai_file("ai_providers.json")
    data = {}
    if project_settings_path.is_file():
        try:
            with open(project_settings_path, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    for ps in settings_in:
        if ps.provider not in PROVIDERS:
            raise HTTPException(422, f"Unknown provider: {ps.provider}")
        data[ps.provider] = {
            "api_key": ps.api_key or data.get(ps.provider, {}).get("api_key", ""),
            "model": ps.model,
            "endpoint": ps.endpoint,
            "context_size": ps.context_size,
            "temperature": ps.temperature,
            "thinking": ps.thinking,
        }
    with open(project_settings_path, "w") as f:
        json.dump(data, f)
    return {"settings": [_masked(p, data) for p in PROVIDERS]}


@router.get("/agents", response_model=AgentPromptsResponse)
def get_agents():
    """Every agent with its current prompt (saved edit, else the built-in default)."""
    saved = _saved_prompts()
    return AgentPromptsResponse(
        agents=[AgentPrompt(name=n, prompt=saved.get(n, d)) for n, d in DEFAULT_PROMPTS.items()]
    )


@router.put("/agents", response_model=AgentPromptsResponse)
def update_agent(prompt: AgentPrompt):
    """Save one agent's prompt. The change is stored apart from the built-in default."""
    if prompt.name not in DEFAULT_PROMPTS:
        raise HTTPException(422, f"Unknown agent: {prompt.name}")
    data = _saved_prompts()
    data[prompt.name] = prompt.prompt
    with open(_ai_file("ai_agents.json"), "w") as f:
        json.dump(data, f)
    return get_agents()


# ---------------------------------------------------------------------------
# Route: models
# ---------------------------------------------------------------------------

@router.get("/models", response_model=ModelsResponse)
def get_models(provider: str = OPENAI):
    """The provider's model list (cached for 1 hour). The server address and key come from the
    saved settings, never from the request: a caller-supplied address would make this route
    fetch any URL on the server's behalf."""
    if provider not in PROVIDERS:
        raise HTTPException(422, f"Unknown provider: {provider}")
    conf = _read_json(_ai_file("ai_providers.json")).get(provider, {})
    endpoint, api_key = conf.get("endpoint", ""), conf.get("api_key", "")
    if provider == LOCAL and not endpoint:
        raise HTTPException(422, "No server address saved for the local model. Add it in AI settings.")

    cache_file = _ai_file("ai_models_cache.json")
    cache = _read_json(cache_file)
    key = f"{provider}|{endpoint}"
    hit = cache.get(key)
    if isinstance(hit, dict) and time.time() - hit.get("ts", 0) < 3600:
        return ModelsResponse(models=hit.get("models", []))

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(modelsUrl(provider, endpoint), headers=headers(provider, api_key))
            resp.raise_for_status()
            models = parseModels(provider, resp.json())
    except httpx.HTTPStatusError as exc:
        raise HTTPException(422, f"{provider} answered {exc.response.status_code} when listing models.")
    except httpx.HTTPError as exc:
        raise HTTPException(422, f"Could not reach {provider}: {exc}")
    except ValueError:
        raise HTTPException(422, f"{provider} sent a model list that is not valid JSON.")

    cache[key] = {"ts": time.time(), "models": models}
    cache_file.write_text(json.dumps(cache))
    return ModelsResponse(models=models)


def _read_json(path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Route: chat history
# ---------------------------------------------------------------------------

@router.post("/chats/new", response_model=NewChatResponse)
def create_chat(req: ChatRequest):
    """Create a new chat and save the first user message."""
    chat_id = ChatStore.new_id()
    first_msg = req.messages[-1]["content"] if req.messages else ""
    agent_name = req.agent or "Co-author"
    title = ChatStore.make_title(agent_name, first_msg)
    project_name = req.project or ""

    chat = {
        "id": chat_id, "title": title, "project": project_name,
        "messages": [{"role": m["role"], "content": m["content"],
                      "agent": m.get("agent")} for m in req.messages],
    }

    with _get_chat_store() as chat_store:
        chat_store.save(chat)
    return NewChatResponse(ok=True, chat_id=chat_id)


@router.get("/chats", response_model=ChatListResponse)
def list_chats(project: str = ""):
    """List recent chats, optionally filtered by project."""
    with _get_chat_store() as chat_store:
        chats = chat_store.list_chats(project if project else None)
    return ChatListResponse(chats=chats)


@router.get("/chats/{chat_id}", response_model=HistoryResponse)
def get_chat(chat_id: str):
    """Load a chat with all its messages."""
    with _get_chat_store() as chat_store:
        chat = chat_store.load(chat_id)
    if not chat:
        raise HTTPException(404, "Chat not found")
    return HistoryResponse(
        id=chat["id"], title=chat["title"], project=chat["project"],
        created=chat["created"], updated=chat["updated"],
        messages=[HistoryMessage(**m) for m in chat["messages"]]
    )


@router.delete("/chats/{chat_id}", response_model=dict)
def delete_chat(chat_id: str):
    """Delete a chat entirely."""
    with _get_chat_store() as chat_store:
        if not chat_store.load(chat_id):
            raise HTTPException(404, "Chat not found")
        chat_store.delete(chat_id)
    return {"ok": True}


@router.put("/chats/{chat_id}", response_model=dict)
def rename_chat(chat_id: str, req: RenameChatRequest):
    """Rename a chat."""
    with _get_chat_store() as chat_store:
        if not chat_store.load(chat_id):
            raise HTTPException(404, "Chat not found")
        chat_store.rename(chat_id, req.title)
    return {"ok": True, "chat_id": chat_id}


# ---------------------------------------------------------------------------
# Route: chat (SSE streaming)
# ---------------------------------------------------------------------------

def _gather_context(chat_req: ChatRequest, project_name: str) -> str:
    """Project context for the model. A missing or unreadable project means no context, but
    the chat still works; anything else is a bug and is logged, not hidden."""
    if not project_name:
        return ""
    try:
        with store.open_project(project_name) as p:
            return context.build(p, chat_req.context_sources, chat_req.scene_id,
                                 chat_req.context_max_tokens)
    except HTTPException:
        return ""  # project not found
    except Exception:
        log.exception("could not build AI context for %r", project_name)
        return ""


async def _stream_chat(chat_req: ChatRequest, request: Request, ctx):
    """SSE generator. Events are one JSON object per `data:` line:
      {"thinking": "..."}                      the next piece of reasoning (local models that think)
      {"text": "...", "inTokens", "outTokens"}   a chunk of the answer
      {"error": "..."}                          the request failed; nothing was saved
      {"done": true, "text", "thinking", "inTokens", "outTokens"}   always last on success
    """
    def sse(obj: dict) -> str:
        return "data: " + json.dumps(obj) + "\n\n"

    chat_store = ctx.__enter__()
    try:
        project_name = chat_req.project
        system = _agent_prompt(chat_req.agent)
        context_text = _gather_context(chat_req, project_name)
        if context_text:
            system = system + "\n\nContext:\n" + context_text

        saved = {}
        try:
            saved = json.loads((_ai_file("ai_providers.json")).read_text())
        except (OSError, ValueError):
            pass
        provider = chat_req.provider
        conf = saved.get(provider, {})
        api_key = conf.get("api_key", "")
        model = chat_req.model or conf.get("model", "")
        endpoint = conf.get("endpoint", "")

        if provider not in PROVIDERS:
            yield sse({"error": f"Unknown provider: {provider}"})
            return
        if not model:
            yield sse({"error": "No model selected. Choose one in AI settings."})
            return
        # A local llama.cpp server has no key; only the cloud providers need one.
        if not api_key and provider != LOCAL:
            yield sse({"error": f"No API key saved for {provider}. Add it in AI settings."})
            return
        if provider == LOCAL and not endpoint:
            yield sse({"error": "No server address saved for the local model. Add it in AI settings."})
            return

        # The browser sends the whole conversation; with none sent, fall back to the saved chat.
        history = chat_req.messages
        if not history and chat_req.chat_id:
            loaded = chat_store.load(chat_req.chat_id)
            history = loaded["messages"] if loaded else []
        conversation = [{"role": m["role"], "content": m["content"]} for m in history]
        if not conversation:
            yield sse({"error": "Nothing to send."})
            return

        payload = buildPayload(provider, model, system, conversation,
                               temperature=chat_req.temperature, thinking=chat_req.thinking)
        url = chatUrl(provider, endpoint, model)
        hdrs = headers(provider, api_key)

        answer = ""
        reasoning = ""
        in_tokens = out_tokens = None
        finished = False

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=15.0)) as client:
                async with client.stream("POST", url, json=payload, headers=hdrs) as resp:
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode("utf-8", "replace")[:300]
                        yield sse({"error": f"{provider} answered {resp.status_code}: {body}"})
                        return
                    async for line in resp.aiter_lines():
                        if await request.is_disconnected():
                            return  # the user pressed Cancel; leaving the block closes the upstream request
                        event = parseStreamLine(provider, line)
                        if event is None:
                            continue
                        if event.error:
                            yield sse({"error": event.error})
                            return
                        if event.inTokens is not None:
                            in_tokens = event.inTokens
                        if event.outTokens is not None:
                            out_tokens = event.outTokens
                        if event.thinking:
                            reasoning += event.thinking
                            yield sse({"thinking": event.thinking})  # just the new piece
                        if event.text:
                            answer += event.text
                            yield sse({"text": event.text, "inTokens": in_tokens, "outTokens": out_tokens})
                        if event.done:
                            finished = True
                            break
        except httpx.ConnectError as exc:
            yield sse({"error": f"Could not connect to {provider}: {exc}"})
            return
        except httpx.TimeoutException:
            yield sse({"error": f"{provider} took too long to answer."})
            return
        except httpx.HTTPError as exc:
            yield sse({"error": f"Request to {provider} failed: {exc}"})
            return

        if not answer and reasoning:
            # It spent the whole budget thinking. Say so rather than show an empty reply.
            yield sse({"error": "The model used its whole token budget thinking and gave no answer. "
                                "Set Thinking to Off, or pick a model that does not think."})
            return
        if not answer:
            yield sse({"error": "The model sent an empty reply."})
            return

        stored = chat_store.load(chat_req.chat_id) if chat_req.chat_id else None
        if stored is not None:
            last_user = next((m for m in reversed(conversation) if m["role"] == "user"), None)
            already = stored["messages"][-1:] == [] or stored["messages"][-1]["role"] != "user" \
                or stored["messages"][-1]["content"] != (last_user or {}).get("content")
            if last_user and already:  # /chats/new may have saved this very message already
                chat_store.add_message(chat_req.chat_id, "user", last_user["content"])
            chat_store.add_message(chat_req.chat_id, "assistant", answer, agent=chat_req.agent)

        yield sse({
            "done": True, "text": answer, "thinking": reasoning, "complete": finished,
            "inTokens": in_tokens or estimateTokens(system + "\n" + "\n".join(m["content"] for m in conversation)),
            "outTokens": out_tokens or estimateTokens(answer),
        })
    except Exception as exc:  # never leave the browser hanging on a half-open stream
        log.exception("chat stream failed")
        yield sse({"error": f"Unexpected error: {exc}"})
    finally:
        ctx.__exit__(None, None, None)


class _ChatStoreContext:
    """Simple context manager for ChatStore that works with generators."""
    def __init__(self):
        self.chat_store = None

    def __enter__(self):
        settings = get_settings()
        store_dir = _ai_file("chats")
        store_dir.mkdir(parents=True, exist_ok=True)
        self.chat_store = ChatStore(str(store_dir))
        return self.chat_store

    def __exit__(self, *args):
        if self.chat_store:
            self.chat_store.close()


def _get_chat_store() -> "_ChatStoreContext":
    """`with _get_chat_store() as store:` opens the chat database and always closes it."""
    return _ChatStoreContext()


@router.post("/chat")
def chat_endpoint(
    chat_req: ChatRequest,
    request: Request,
):
    """Stream a chat completion via SSE."""
    ctx = _ChatStoreContext()
    return StreamingResponse(
        _stream_chat(chat_req, request, ctx),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
