# manuskript-ai-web: build plan

A self-hosted, single-user, phone-first web rewrite of the Manuskript AI fork.
**Status (13 Oct 2026):** Phases 0-3 complete. Phase 4 (AI) now works end to end: a live chat against the llama.cpp server streams, uses the open scene as context and saves (see its section). Phase 5 done. Phase 6: outline, corkboard, whiteboard done; storyboard (flow diagram) replaced by whiteboard; storyline and drag-and-drop not started. Phase 7 (Google Drive) is **dropped**; files will be synced another way (see Phase 7). Next: Phase 8 UI (search, revisions, export/import), then Phase 9 hardening.

**How this was last verified:** server 308 pytest, web 138 vitest, 18 Playwright (+2 live AI tests, run on demand) (phone 390x844 and desktop 1440x900), svelte-check 0 errors. Run them with the commands in README.md.

## Progress Summary

| Phase | Status | Notes |
|---|---|---|
| 0: skeleton, Docker, login | ✅ Done | Auth, TOTP, rate limiting, PWA, login page, route guards. Extra accounts can be created from More (admin-only), which no longer logs the admin out. |
| 1: msklib (project file library) | ✅ Done | Byte-identical round trips, zipped `.msk` read, 30+ pytest tests |
| 2: server API | ✅ Done | Projects, outline, records, plots/world, search, revisions, references, settings, events (SSE), lock/423. Project templates added (see Phase 6b). Every route is now checked for login by one test that walks the whole route table. |
| 3: editor, icon toolbar, design system | ✅ Done | CodeMirror editor with line wrapping, formatting toolbar, autosave, version conflicts, word count, session goal, typewriter and line focus, 32 themes. An empty scene now gets an editor (it used to show none). |
| 4: AI assistant | ✅ Done (local model) | Repaired and run live against llama.cpp on 11 Oct 2026. Anthropic, Gemini and OpenAI have parser/payload tests but have not been run against real accounts. See the Phase 4 section. |
| 5: characters, plots, world | ✅ Done | Full CRUD, search, inspector, general+summary, labels. Undo after delete now really re-creates the item on the server. Remaining: bulk actions, virtualised lists (Phase 6). |
| 6: corkboard, outline, storyline | 🔄 Partial | Outline, Cards (corkboard), and Board (whiteboard) done and tested. Storyboard (flow diagram) was fully replaced by the whiteboard (free-form canvas, drag/zoom/pan via SvelteFlow). Not started: touch drag and drop, outline table, folder views, storyline, bulk actions, virtualised lists. |
| 6b: project templates | ✅ Done | Save a project's structure as a template, start new projects from it. Not in the original plan. |
| 6c: whiteboard, storyboard removal | ✅ Done | Board (whiteboard) replaces storyboard. Free-form canvas via `@xyflow/svelte` with shape/note/scene-card nodes (blank default shape labels, editable labels, hover + toggleable notes, icon node removed), centered toolbar, custom `DashedEdge` supporting 4 line styles (`solid`, `dash`, `dot`, `solid-dashed`) with live button preview that activates connection mode, and localStorage persistence. Old storyboard (`Cards` route) fully deleted. |
| 7: Google Drive sync | ❌ Dropped | Decision 11 Oct 2026: not building Google integration. Project files will be synced another way (rsync, Syncthing or a mounted folder; see Phase 7). |
| 8: export, import, search, goals, revisions | ⬜ Pending | **Server side is only partly done.** Search, revisions, `.msk` import and zip upload/download exist as API. Export (pandoc/WeasyPrint), compile and Markdown/OPML import do NOT exist yet (an earlier note here said they did). No UI for any of it. |
| 9: hardening, backups, install guide | ⬜ Pending | Partly done early: see "Security fixes so far" in Phase 9. |
| 10: Dropbox | ❌ Dropped | Same decision as Phase 7. |
| 11: offline writing | ⬜ Pending | Deferred |

---
## 1. Decisions (locked)

| Topic | Decision |
|---|---|
| Repo | /home/ab/workspaces/manuskript-ai-web (new, GPL-3.0, reuses desktop-fork code) |
| Host | Proxmox VM (Debian 12 + Docker), 4 cores / 16 GB. Develop and test on the Ubuntu rig |
| Access | Home VPN + own reverse proxy + own domain. App speaks HTTP inside the LAN; the proxy does HTTPS |
| Users | Password login with optional TOTP two-factor. The first account is created on first visit; the owner can add more from More | 
| File sync | No cloud integration (decided 11 Oct 2026). Project folders are synced by an outside tool; see Phase 7 |
| File format | MUST stay compatible with desktop Manuskript (same project folder, byte-identical round trip) |
| Offline writing | Deferred (Phase 11), after the web app is fully functional |
| Phone | Critical. Every screen is designed phone-first, then scaled up |
| AI | llama.cpp (Docker host 10.0.0.80:8180), OpenAI, Anthropic, Gemini, same four roles as the desktop fork |

## 2. Architecture

| Part | Choice | Why |
|---|---|---|
| Server | Python 3.12, FastAPI, uvicorn | Reuses the existing Python AI code; native SSE streaming |
| Project storage | Manuskript folder format on disk | Same files desktop Manuskript opens |
| App database | SQLite (WAL) | Users and login attempts (sessions are signed cookies, not stored). (AI chats, provider settings and agent prompts live in `data/app/ai/`, see Phase 4.) |
| Browser app | SvelteKit + TypeScript, built as a static PWA | Fast on phones, installs to the home screen |
| Editor | CodeMirror 6 + live Markdown styling | Keeps text byte-exact (tabs, special spaces); rich-text editors rewrite Markdown |
| Icons | Lucide | Clean, consistent, icon-led toolbar |
| Touch drag and drop | SortableJS | Outline and corkboard reordering by touch |
| File sync | Outside the app (Syncthing, rsync or a mounted folder) | The server edits plain folders and never caches them, so any file-level sync works; the `.lock` marker keeps a pass from racing a save |
| Export | pandoc + WeasyPrint in the container | DOCX, EPUB, ODT, HTML, PDF |
| Deployment | Docker Compose, one image + a data volume | `docker compose up -d` |

## 3. Reuse map (copy from the desktop fork, do not re-write)

| Source (desktop fork) | Goes to | Change needed |
|---|---|---|
| manuskript/ai/providers.py (207 lines) | server/app/ai/providers.py | none, it has no Qt |
| manuskript/ai/context.py (117) | server/app/ai/context.py | read from msklib instead of Qt models |
| manuskript/ai/chats.py (68) | server/app/ai/chats.py | none (JSON store) |
| manuskript/ai/config.py (role prompts) | server/app/ai/prompts.py | drop QSettings, keep DEFAULT_PROMPTS |
| manuskript/appearance/schemes.py, colors.py | web/src/lib/themes (TS port) + server copy for tests | port 31 schemes to TypeScript data |
| manuskript/load_save/version_1.py (1137) | server/msklib | REWRITE without Qt (reads/writes the same files) |
| manuskript/exporter/* | server/app/export | use pandoc directly |
| Everything under manuskript/ui (16,300 lines) | web/src | REBUILD as Svelte screens, not ported line by line |

## 4. Repository layout

```
manuskript-ai-web/
  PLAN.md  README.md  COPYING  docker-compose.yml  Dockerfile  .env.example
  server/
    pyproject.toml
    app/
      main.py            FastAPI app, routers, static files
      config.py          env settings (pydantic-settings)
      auth/              login, sessions, TOTP, rate limiting
      api/               projects, outline, documents, characters, plots, world, labels, settings, templates, ai, export (export not built yet)
      ai/                providers.py context.py chats.py prompts.py
      export/            pandoc + weasyprint
      db.py              SQLite schema + migrations
    msklib/              Qt-free Manuskript project reader/writer (the core)
    tests/
  web/
    package.json  svelte.config.js  vite.config.ts
    src/
      routes/            /login /p/[project]/(write|outline|cards|characters|plots|world|summary|settings)
      lib/               api client, stores, themes, icons, components
      lib/editor/        CodeMirror setup + toolbar
    static/              manifest.webmanifest, icons, service worker
  deploy/                Caddyfile.example nginx.conf.example proxmox-vm.md backup.sh
  docs/                  install.md  archive/google-drive-research.md  (to write: syncing.md reverse-proxy.md phone.md backup-restore.md)
```

## 5. Cross-cutting rules (apply to every phase)

1. **Phone first.** Design at 390 px wide, then enlarge. Touch targets at least 44 px. No hover-only features.
2. **Files are the source of truth.** The server edits the Manuskript folder directly. SQLite never holds project content.
3. **Round-trip safety.** Load then save must reproduce files byte for byte unless the user changed them. Tested on every phase that touches msklib.
4. **Single writer.** One server process owns the project folder, with a per-project lock and a version number on every document, so a stale save is rejected instead of overwriting.
5. **No silent deletes.** Deleting moves items to `.trash/` inside the data volume. Sync never deletes remotely without a snapshot.
6. **Secrets.** API keys and cloud tokens are encrypted at rest (Fernet key from `.env`), never logged, never sent to the browser after being saved.
7. **Tests are part of the phase.** pytest for server and msklib; Playwright for browser at 390x844 and 1440x900 widths; screenshots saved for review.
8. **One commit per step**, conventional-commit messages, `main` stays green.
9. **Streaming.** AI replies use Server-Sent Events; Cancel closes the stream and the upstream request.
10. **Accessibility basics.** Keyboard reachable, visible focus, contrast checks on all 32 themes (reuse the WCAG test from the desktop fork).

## 6. Phase 0: skeleton, Docker, login (2-3 days)

Goal: log in from your phone and see an empty app shell, served by Docker.

1. Create `server/` with FastAPI, `GET /api/health`, settings from environment.
2. Create `web/` with SvelteKit (static adapter), a phone-first shell: top bar, bottom navigation (Write, Outline, Cards, Characters, More), theme variables.
3. Dockerfile (multi-stage): build web, then Python image serving API + static files. Installs pandoc, rclone and the WeasyPrint libraries. (`rclone` is no longer used by anything since Google sync was dropped; it is left in the image in case you use it for your own sync scripts, and can be removed to shrink the image. `pandoc` is installed for the unbuilt export in Phase 8.)
4. docker-compose.yml: one service, volumes `/data/projects`, `/data/app`, port 8000. `.env.example` lists every variable.
5. Auth: first-run "create your account" page (only works while no user exists). Argon2id password hash, signed session cookie (HttpOnly, Secure, SameSite=Lax), logout, CSRF token for state-changing calls.
6. Brute-force protection: per-IP and per-account rate limit, increasing delay after failures.
7. Optional TOTP two-factor: setup page with QR code, 10 recovery codes, enforced at login once enabled.
8. Reverse-proxy awareness: trust `X-Forwarded-*` only from configured proxy addresses; optional allowlist of LAN/VPN CIDR ranges for login.
9. PWA basics: manifest, icons, install prompt, theme colour.
10. Tests: auth flow, rate limit, CSRF, health. Playwright: login at 390x844 and 1440x900.

Done when: `docker compose up -d`, log in on your phone over the VPN, install to the home screen.

## 7. Phase 1: msklib, the project file library (3-5 days)

Goal: a Qt-free Python library that reads and writes the desktop project format with a byte-identical round trip.

**Format facts (from the current project and version_1.py):**
- `Name.msk` is a marker file; the project lives in the folder `Name/`.
- `outline/` holds one folder per outline folder, named `<index>-<Slug>/`, with `folder.txt`; scenes are `<index>-<Slug>.md`. Slug = letters and digits kept, whitespace to `_`, anything else to `-`.
- Scene file = MMD-style header (`title:`, `ID:`, `type:`, `compile:`, `charCount:` ... padded to a 10-column tab), then a blank line, then the text. Multi-line values are indented. `:` in a key is escaped as `_.._`.
- `characters/<index>-<Slug>.txt`: same header style, one file per character.
- `plots.xml`, `revisions.xml`, `world.opml`: XML/OPML (lxml-written, so keep attribute order and escaping).
- `settings.txt`: JSON, 4-space indent. `labels.txt`, `status.txt`, `infos.txt`, `summary.txt`: simple text files.
- Saving renumbers and renames files when items move; an unchanged project must write nothing.

Steps:
1. Define dataclasses: Project, OutlineItem (folder/md/t2t/html/opml), Character, Plot, PlotStep, WorldItem, Label, Status, Settings.
2. Reader: parse every file above into the dataclasses. Keep the raw text of anything not understood, so nothing is lost.
3. Writer: reproduce the exact formatting rules above (padding, escaping, slug, indexing, JSON indent, XML declaration).
4. Change tracking: write only files whose content changed; move/rename files when order or title changes; delete obsolete files into `.trash/`.
5. Support the zipped `.msk` variant read-only at first (the folder format is the priority).
6. **Golden tests (the key safety net):**
   - Load then save your `MSK/Draft-0001` project into a temp folder; assert every file is byte-identical.
   - Same for `sample-projects/book-of-acts`.
   - Mutation tests: rename a scene, move it, add a character, edit a plot step, change a label; save; then open the result with the real desktop Manuskript headless (offscreen test) and assert the data matches.
7. Property tests (hypothesis): random titles with unicode, colons, tabs, no-break spaces; round trip must be stable.
8. Word and character counts that match desktop Manuskript (same rules for counting spaces).

Done when: golden tests pass for both projects and desktop Manuskript opens msklib-written projects without any difference.

## 8. Phase 2: server API (4-6 days)

Goal: every project operation available over REST, safely.

1. Projects: list, open, create (blank or from the sample), rename, delete to trash, download as zip, upload zip.
2. Outline: tree read; create, rename, move (drag and drop), delete, set label, status, compile flag, POV character, summary, goal.
3. Documents: read and save scene text. Every document carries a `version`; a save with a stale version returns 409 and the browser shows a merge prompt, never overwrites.
4. Characters, plots (with steps and links to characters/scenes), world tree, labels, statuses, book info and summaries, project settings.
5. Locking and writing: one lock per project, atomic file writes (write temp, fsync, rename), and a `.lock` marker while a sync pass is running (writes get 423, reads still work). DONE. **No server-side write queue, on purpose:** a save is only acknowledged once it is on disk, which is what makes the stale-save 409 trustworthy. Debouncing happens in the browser editor (Phase 3). Measured with `server/tools/bench_scale.py`: one save request on a 2000-scene, 10 MB project takes about 64 ms.
6. Revisions: snapshot a scene on save at the same intervals as desktop Manuskript (settings.revisions rules).
7. Search: full-text across scenes, notes, characters, with filters. DONE. **No FTS5 index, on purpose:** the files are the source of truth and the desktop app and sync edit them behind our back, so an index could show stale results. Scanning the files per request measured about 90 ms on a 2000-scene, 10 MB project. Revisit only if a real project makes search slower than about half a second.
8. Events: a `/api/events` SSE stream so open tabs refresh when something changes (second device, sync pass).
9. OpenAPI schema generated and TypeScript client generated from it.
10. Tests: API tests for each endpoint, concurrency test (two simultaneous saves), kill-during-write test (power-loss safety), and the msklib golden tests rerun through the API.

Done when: the whole project can be edited through the API and desktop Manuskript still opens it.

## 9. Phase 3: editor, icon toolbar, design system (1.5-2 weeks)

Goal: write a chapter comfortably on a phone and a desktop.

**Design system**
1. Theme engine: the 31 desktop schemes + System as TypeScript data, applied as CSS variables, switchable LIVE (no restart), dark-first default (Midnight). Contrast test reused from the desktop fork.
2. Components: Button, IconButton, Sheet (bottom sheet on phone, side panel on desktop), Drawer, Tabs, Menu, Dialog, Toast, Segmented control, Slider. Rounded corners, generous spacing, one accent colour, Inter font bundled.
3. Density setting (Compact, Comfortable, Spacious), interface font and size.
4. Responsive shell: phone = bottom navigation + drawers; tablet = collapsible outline rail; desktop = three panes (outline | editor | AI/inspector), all resizable and remembered.

**Editor (CodeMirror 6)**
5. Markdown with live styling (headings, bold, italic, quotes, lists shown formatted, markup dimmed when the cursor is away). The stored text is never changed except by the user.
6. Preserve exactly: tabs, no-break spaces, trailing spaces, line endings, curly quotes.
7. Tab key inserts a tab; tab width setting counts SPACES (the fixed desktop bug), first-line indent in the same unit.
8. Autosave with debounce, a saved/saving/offline indicator, version-conflict prompt (keep mine, keep theirs, compare).
9. Spell check: browser spell check on, plus custom dictionary stored on the server.
10. Word count, character count, session goal and progress ring; typewriter mode, focus mode (sentence/line/paragraph), distraction-free mode.

**Icon-led formatting toolbar (Lucide)**
11. Buttons with tooltips and long-press labels: Bold, Italic, Strikethrough, Heading 1-3, Quote, Bullet list, Numbered list, Link, Comment, Undo, Redo, Focus, Typewriter.
12. Paragraph style menu (Body, Heading 1-4, Quote, Bullet, Numbered) that acts on all selected paragraphs, same logic as the desktop formatting bar.
13. "More" menu: alignment, line spacing, space below paragraph, indent, tab width, font and size (same settings as desktop).
14. Phone: toolbar docks above the on-screen keyboard (visualViewport API), scrolls horizontally, thumb-sized buttons.
15. Keyboard shortcuts on desktop (Ctrl+B/I, Ctrl+K command palette, Ctrl+S, Ctrl+F).

**Navigation**
16. Outline drawer/pane: tree with icons, labels (colour dots), status chips, progress; drag handles for reorder; swipe actions (rename, delete, label).
17. Tabs for several open scenes; split view on wide screens.

**Tests**: Playwright at 390x844 and 1440x900: type, format, autosave, conflict prompt, theme switch, reorder; visual snapshots of all 32 themes for the editor.

Done when: you can write and format a chapter on your phone and desktop, and desktop Manuskript opens the result unchanged.

**Remaining Phase 3 items (post-core):**
- [x] Spell check (browser built-in — custom dictionary server-side)
- [x] Typewriter mode, line focus mode
- [x] Spell check custom dictionary (server-side word list)
- [x] Scene tabs (multiple open scenes)
- [x] Split view on wide screens
- [x] Paragraph style menu (acts on selected paragraphs)
- [x] Comment button
- [x] Full desktop keyboard shortcuts (Ctrl+B/I/K)

---

## 10. Phase 4: AI assistant (3-5 days)

Goal: parity with the desktop AI dock, plus streaming over the web.

**Status (11 Oct 2026): done for a local llama.cpp model; cloud providers untested live.** This phase was first marked "complete" when it was not (most UI calls failed). It was repaired, then run against a real llama.cpp server (`Qwen3.5-9B-UD-Q4_K_XL`), which found a second round of bugs that only a real model exposes. All of it is below.

| Problem found | Fix |
|---|---|
| **No login on any AI route.** Anyone who could reach the server could read provider settings, list chats, and call `/api/ai/chat` (which spends cloud credits). | The whole router now requires a login. A test walks every route in the app and fails if one is open (`test_all_routes_require_login.py`). |
| `GET /chats`, `POST /chats/new`, every chat route: crashed (`_get_chat_store` was never defined). | Defined. Round trip tested. |
| `GET /providers` crashed (`provider` missing from the saved record). | Fixed; settings are returned as `{settings: [...]}`, which is what the UI reads. |
| API keys were meant to be write-only but the settings form could wipe a saved key by saving a blank one. | Blank key now means "keep the saved key". The response says `has_key: true` instead of returning the key; tested that a key never appears in a response. |
| UI called routes that do not exist: `/providers/{p}/models`, `PUT /agents` (server had `PATCH` taking a list), and `POST /chat` to create a chat. | UI now calls `/models?provider=`, `PUT /agents` (one prompt), and `/chats/new`. Models are cached per provider and endpoint (one provider's list was being served for all). |
| Agent prompt edits were saved but never used when chatting. | Saved prompt is used; tested. |
| The chat request did not send a CSRF token, and the store used a hardcoded project `book-of-acts`. | Sends the token; follows the selected project. |
| **The context builder never worked.** It called methods that do not exist (`outline.get_current_scene`, `p.info`, `characters.get_character`), and a blanket `except: pass` hid it, so the model was always sent **no project context**. A probe confirmed the context string was empty. | Rewritten as `server/app/ai/context.py` over the real msklib model (7 tests). The UI now sends the open scene's id, so the model sees the scene text, its summary and notes, its POV character and the book info, trimmed to the token budget (a long scene keeps its end). Failures are logged, not swallowed. |

**Found only by running a real model (live run, 11 Oct 2026):**

| Problem | Fix |
|---|---|
| A local model could never chat: the code demanded an API key for every provider, and llama.cpp has none. | Only cloud providers need a key. |
| A thinking model (Qwen) spent all 4,096 tokens reasoning and sent no answer. "Thinking: Off" sent `reasoning_effort`, which llama.cpp ignores. | Off now sends `chat_template_kwargs: {enable_thinking: false}`, the flag the model honours. First reply went from endless thinking to about 2 s. If a model still only thinks, the user gets an explicit error instead of an empty reply. |
| The reasoning text was thrown away (parser kept a yes/no flag). | `StreamEvent.thinking` carries the text; streamed apart from the answer. |
| **Replies were never saved and no final event was sent.** A misplaced `return` made the save and the `done` event unreachable. | `_stream_chat` rewritten with one event contract (documented in its docstring) and a clear error for each failure (bad model, unreachable server, upstream 4xx, empty reply, timeout). |
| `GET /models` failed every time (missing import), so the model dropdown could never load. | Fixed. |
| **`GET /models` fetched any URL the caller passed** (SSRF). | Address and key now come from saved settings only; a request-supplied `endpoint` is ignored (tested). |
| The first message of a chat could be saved twice. | De-duplicated (tested). |

**What was verified live:** the reply streams (about 33 chunks for a one-sentence answer); the open scene reaches the model (a made-up password planted in a scene summary was quoted back when the summary source was on, and not when it was off or no scene was open); Cancel stops the stream and saves nothing; a nonexistent model, an unreachable server and a missing address each give a readable error; the real chat panel in a browser gets the planted fact and the turn is saved (`web/e2e/ai-live.spec.ts`, runs only when `MSK_LLAMA_URL` is set). The regression tests use a fake model server whose message shapes were copied from the live run, and three of the fixes were reverted one at a time to confirm the matching tests fail.

Completed:

1. ✅ **Providers** (`server/app/ai/__init__.py`): URL builders, headers, payloads and SSE stream parsers for llama.cpp, OpenAI, Anthropic and Gemini; model-list parsers; `estimateTokens`. No Qt.
2. ✅ **Chat history** (`server/app/ai/history.py`): SQLite `ChatStore` in `data/app/ai/chats/`, chats tagged by project.
3. ✅ **Routes** (`server/app/ai/routes.py`): `GET/POST /providers`, `GET /models`, `GET/PUT /agents`, `POST /chats/new`, `GET /chats`, `GET/PUT/DELETE /chats/{id}`, `POST /chat` (SSE streaming). Login required on all.
4. ✅ **Context builder** (`server/app/ai/context.py`): per-source toggles (selection, scene, summary, POV, book).
5. ✅ **Agent prompts**: four built-ins (Co-author, Editor, Publisher, Reader), editable, saved in `data/app/ai/ai_agents.json`.
6. ✅ **UI**: AI settings page, chat panel, chat history (list, rename, delete), status line, editor extras.

Still open (none of these block using it with a local model):

7. ⬜ **Cloud providers**: Anthropic, Gemini and OpenAI have parser and payload tests only. Run one chat against each you plan to use. Also untested: a thinking model with Thinking switched on in the browser (it works over the API but took 140 s to answer "2+2" on this model), and Cancel from the browser button (tested at the connection level only).
8. ⬜ **Selection as context**: the "selection" toggle is sent but the server only uses the scene, summary, POV and book sources. Today the selected text reaches the model only because "Ask AI about selection" puts it in the message.
9. ⬜ **Keys are stored as plain text** in `data/app/ai/ai_providers.json` (the code comment says so). Acceptable for a single-owner box behind a login, but note it in the install guide, and consider encrypting with a key derived from `MSK_SECRET_KEY`.
10. ⬜ **Spend limits** (Phase 9 item 2).

Done when: a chat streams from your llama.cpp server with the open scene as context, the model can be switched mid-chat, history persists, and Cancel stops the upstream request. **Met for the local model.**

## 11. Phase 5: characters, plots, world, summary, general (about 1 week)

Goal: every non-editor data screen, phone friendly, writing the same files as desktop.

1. ✅ **Characters:** list with avatar colour/initials, search, importance; detail form with the desktop fields (name, motivation, goal, conflict, epiphany, summaries, notes, infos, importance, colour).
2. ✅ **Plots:** list with importance; resolution steps with summaries; linked characters.
3. ✅ **World:** OPML tree editor (add, nest, edit, delete) with a detail form and search.
4. ✅ **General and Summary screens:** book info and the snowflake summary fields.
5. ✅ **Labels and statuses:** manage names and colours.
6. ✅ **Inspector panel** in the editor: label, status, summary, goal, POV (now a character picker), notes.
7. ✅ **Empty states and undo after delete.** Undo used to put a fake, mostly-empty record back in the *list* while the server still had it deleted, so it vanished on reload. It now re-creates the item on the server (it gets a new id; a world item's children are re-created too). Tested for characters in Playwright; plots and world use the same pattern but have no UI test yet.
8. ⬜ **Tests**: the character create/undo flow has a Playwright test; plots, world, labels and the settings screens have none. The desktop cross-check tests (msklib output opens in desktop Manuskript) pass.

Known rough edges: the form-based screens each carry their own copy of the same list/form code; a shared component would cut about a third of the code and the bugs found here (missing `$state`, missing project name) came from that duplication.

Done when: you can build characters and a plot on your phone and see the same data in desktop Manuskript. **Mostly met; needs a manual check of plots and world on a phone.**

## 12. Phase 6: corkboard, outline table, storyline (1-1.5 weeks)

Goal: the visual views, usable by touch.

**Project selection (done, cuts across every screen).** The app used to hardcode a project called `book-of-acts` in six screens, so most of it only worked for one sample project. The selected project (chosen in More) is now used by Write, Outline, Cards, Characters, Plots, World, Labels, Settings and AI chat; each shows a "choose a project" prompt instead of calling the server when none is selected.

**Label and status format (fixed).** Desktop Manuskript stores an item's label and status as a 1-based position in `labels.txt` / `status.txt` (`""` or `0` = none). The web UI was writing the *name*, which desktop reads as "no label". The UI now writes positions and the server refuses names or out-of-range numbers (422). Verified end to end: pick a label in the outline, the API and the file hold the position, and it survives a reload.

1. ✅ **Outline** (`/outline`): tree and table views with expand/collapse, chapters created as `folder` items (labeled `Chapter`) so scenes index underneath chapters rather than inline (`resolveParentForAdd`), indented child rows in table view (`flattenWithDepth`), inline rename (Enter and blur no longer double-save), delete with a trash confirmation that names the folder contents, label buttons and status select with the real colours, summary sentence, associated notes on both chapters and scenes (added via `+` menu or detail panel; inline table `notes` column removed), and "Open in editor". Keyboard-operable.
2. ✅ **Corkboard** (`/cards`): cards for the current folder with title, summary, label colour stripe, status chip and word count (new `words` field on every outline item); breadcrumb into folders; add a scene; move a card earlier/later or out of its folder; the new order is written to the project files. Reordering uses buttons, not dragging.
3. ✅ **Storyboard flow diagram** (`/cards`, default view): a deterministic flow diagram showing the folder's scenes in outline order as numbered cards connected by chevron arrows. Each card shows a colour badge, a title, a summary clamp, a status chip, and a word count. No free-form dragging — order is controlled by action-bar arrows (swap earlier/later or move into/out of a folder). Folder boundaries appear as grouping containers. The flow is always recomputed from the outline (no persisted node positions); the API provides `GET/POST /api/projects/{name}/outline` and `POST .../outline/{id}/move`. Pure-logic modules (`storyboard.ts`) handle `sceneFlow`, `moveInFlow`, and `moveOutOfFolder` with 5 unit tests; `Storyboard.svelte` renders the serpentine grid and `StoryboardCard.svelte` renders each scene card. No external canvas library used.
4. ⬜ **Touch drag and drop** (SortableJS is not installed): long-press to lift, auto-scroll, drop between cards or into a folder.
5. ⬜ **Outline table**: sortable columns, column picker, inline editing; stacked rows on a phone.
6. ⬜ **Folder views** (text, cork, outline) per folder, saved in project settings like desktop.
7. ⬜ **Storyline**: plots as lanes against the scene sequence.
8. ⬜ **Bulk actions**: select several items to set label, status, compile flag, or move.
9. ⬜ **Performance**: virtualised lists for a 2,000-scene project. The outline page re-fetches the whole tree after each delete or move; fine for hundreds of scenes, unmeasured beyond that.
10. ⬜ **Cards, card size slider, paper-card option, background colour** from the original corkboard item.
11. ⬜ Visual snapshots in all themes; touch emulation in Playwright.

Done when: you can reorganise chapters by touch and desktop Manuskript shows the new order. **Not yet met:** order can be changed by buttons, not by dragging.

## 12b. Phase 6b: project templates (added 11 Oct 2026, not in the original plan)

Save a project's structure as a template and start new projects from it.

1. ✅ **Server** (`server/app/api/templates.py`, `projects.py`): templates are plain project folders in `data/templates/`. `GET/POST /api/templates`, `DELETE /api/templates/{name}` (moves to `templates/.trash`), and `POST /api/projects` accepts `template`. Revision history is never copied; by default scene text is emptied so only the structure remains (`keep_text` keeps it). A new project from a template is an independent copy with its own title. 8 tests: structure-only, keep text, independence, name guards, duplicates, failed attempts leaving nothing behind, trash.
2. ✅ **UI** (More): a bookmark button on each project saves it as a template; the Create form has a template dropdown (and picking a sample clears it); a templates list with delete.
3. ⬜ **Not done:** a template made from a project with a character, plot or world item copies them in full; there is no separate editor for "placeholder" characters. Scene-level templates (a reusable "chapter" snippet) are not built; the request that started this was cut off, so project templates were built.

## 13. Phase 7: syncing project files (replaces the Google Drive plan)

**Decision, 11 Oct 2026:** no Google integration. Files are synced another way, outside the app. The Google Drive design, its OAuth findings and its rclone safety rules are archived in `docs/archive/google-drive-research.md` (nothing in the app depends on them).

Why this is cheap: the server edits the Manuskript project folders under `data/projects/` directly and never caches them (PLAN section 5, rule 2). So any tool that keeps that folder in step with another machine works, with no code in this app. These parts already exist and are what a file-level sync relies on:

- **`.lock` marker** (`server/app/synclock.py`, tested). While a `.lock` file is in a project folder the web app refuses to *write* (reads still work, HTTP 423), so a sync pass never sees a half-changed project. A marker older than 15 minutes is treated as stale and ignored, so a crashed script cannot lock a project forever. Dot-files are ignored by msklib and by desktop Manuskript.
- **Live refresh.** While at least one browser tab is open, a background watcher polls the project folders and publishes an SSE event when files change on disk (second device, sync pass), so that tab updates. With no tab open it does nothing, which is fine: the next page load reads the files fresh.
- **Stale-save protection.** Saving a document sends the version it was loaded from; if the file changed underneath (desktop edit, sync), the server answers 409 with the on-disk text instead of overwriting.
- **Nothing is hard-deleted.** Deleted scenes, projects and templates move to `.trash/`.
- **Whole-project zip** download and upload (`/api/projects/{name}/download`, `/upload`), and `.msk` import.

What is left, all small and optional:

1. ⬜ **`docs/syncing.md`**: how to use one of these, with the `.lock` convention (create `data/projects/<name>/.lock` containing JSON `{"owner": "...", "at": <unix seconds>}` (`at` is required; `owner` and `pid` are informational; see `synclock.py`) before a pass, and delete it after). Options to document: Syncthing (continuous, both ways), rsync/rclone on a timer (one way is safest), or a mounted network folder. Recommend one device edits at a time, and exclude `.trash/` and `.lock` from the sync.
2. ⬜ **Conflict behaviour for two-way tools**: Syncthing keeps both versions as `.sync-conflict` files, which msklib would read as stray files. Decide whether msklib should ignore them, or whether the doc should tell people to exclude that pattern. Not yet tested.
3. ⬜ **A "Download everything" backup button** is Phase 9 item 3; it also covers the case where you only want a manual copy.

Not being built: OAuth, token storage, an in-app sync screen, conflict-resolution UI for sync.

Done when: `docs/syncing.md` exists and one real two-machine run (edit on the web app, see it on the desktop app and back) has been tried and written up honestly, including what went wrong.

## 14. Phase 8: export, import, search, goals, revisions (about 1 week)

**What exists on the server (tested):** project-wide search, a scene's revisions (list, read, restore), cross-references and broken-link reports, whole-project zip download/upload, and import of a desktop `.msk` zip (`/api/projects/import-msk`).

**What does NOT exist (an earlier version of this plan said it did):** export of any kind, compile, Markdown/plain-text/OPML/DOCX import, goals and history, frequency analyser. `pandoc` is installed in the Docker image but no server code calls it, and WeasyPrint is not a dependency. **There is no UI for any item below**, including the parts whose API exists.

1. ⬜ **Export (server side, pandoc):** Markdown, plain text, HTML, DOCX, ODT, EPUB, and PDF (HTML to PDF with WeasyPrint, so no LaTeX install is needed). Choose which items to include (the compile flags), separators, title page, and a simple style choice. Preview in the browser before download; large exports run as a background job with progress. *Server and UI both to build.*
2. ⬜ **Desktop compile parity:** the same compile flags, scene separators and the Manuskript "basic" outputs, tested by comparing against desktop output for the sample project.
3. ⬜ **Import:** Markdown or plain-text files and folders, OPML, DOCX/ODT/EPUB through pandoc, with a dry-run preview. (`.msk` zip import exists as API, no UI.)
4. ⬜ **Search UI:** API exists (file scan, no index, about 90 ms on a 2,000-scene project). Needs a results screen that jumps to the match, and a command palette (Ctrl+K and a search icon on phone).
5. ⬜ **Word-count goals:** per-scene goal is stored (`setGoal`) and shown in the Inspector; there is no project goal, daily goal, streak or history. The editor's session goal is a fixed 500 and not saved.
6. ⬜ **Revisions UI:** API exists. Needs a list per scene, a diff against the current text, and one-tap restore (restoring itself creates a revision).
7. ⬜ **Frequency analyser and spell language.**
8. ⬜ Tests: export a golden project and compare text content; import then export round trip.

**Suggested order**, smallest and most useful first: Search UI (4), Revisions UI (6), then Export (1) because it is the biggest unknown and the one a finished book needs. Export is the next item I would build.

Done when: a DOCX and an EPUB export open correctly, import of a Markdown manuscript works, and search finds text across the project.

## 15. Phase 9: hardening, backups, install guide (about 1 week)

**Security fixes so far** (found while reviewing, each with a regression test):

- All AI routes were reachable without logging in. Now the router requires login, and `test_all_routes_require_login.py` fails if any future route is left open (65 checks across every route in the OpenAPI schema).
- `POST /api/auth/register` used to log the admin into the *new* account (session hijack on create). It now leaves the caller's session alone.
- Provider API keys are never returned by the API (`has_key` only).
- `GET /api/ai/models` could be made to fetch any URL; it now uses only the saved address.
- Project, template and sample names are validated against path traversal; template create/delete is covered by tests.
- `/register` is no longer reachable as a public page; the page redirects to login.

Still to do:

1. ⬜ **Security review:** run an automated dependency audit; secure headers (CSP, HSTS via the proxy, no sniffing, frame denial); upload size and type limits (zip size caps exist, other limits unchecked); path-traversal tests on every file API (names are validated; not every route has its own test); zip-slip tests (both upload and `.msk` import are tested with a `../escape` entry); SSRF: `GET /api/ai/models` no longer accepts an address from the request (fixed, tested). The saved llama address is still whatever the owner typed, which is fine for a single-owner box. The chat route also posts to that saved address.
2. ⬜ **Rate limits** on login (done), AI calls (not done: a stuck page can still run up a cloud bill), and exports. A monthly AI-spend counter per provider.
3. ⬜ **Backups:** nightly snapshot of `data/projects` and `data/app/app.db` to a separate volume, restore tested; one-click "download everything" zip (per-project zip exists).
4. ⬜ **Logging and health:** `/api/health` exists; add structured logs with secrets stripped, `/api/ready`, a status page (disk, last backup).
5. ⬜ **Updates:** versioned database migrations; the schema is `CREATE TABLE IF NOT EXISTS` today, so a column change would need migration code first.
6. ⬜ **Docs:** `docs/install.md` exists and is accurate for first run; still needed: reverse-proxy (Caddy and nginx examples exist in `deploy/`; add SSE/no-buffering notes for the AI stream), phone install notes, backup/restore, **syncing** (Phase 7), and a note that AI keys are stored as plain text.
7. ⬜ **Performance pass:** load test with 2,000 scenes and 500,000 words on a phone emulation; lazy-load the editor (the main JS bundle is about 620 kB, above the build tool's warning limit).
8. ⬜ **A week of real use** on your own manuscript before calling it done.

Done when: restore from backup is proven, the security checklist is clean, and the guides get a fresh VM to a working login.

**Housekeeping found:** the dev server on port 8081 stores data in `/tmp/manuskript`, which the OS may clear; use a real folder for anything you care about. README still says "Google Drive sync" in its first line, which is stale.

**Docker launch bug (found 12 Oct 2026, fixed).** A fresh `git clone` + `docker compose up` built fine but the app crashed at start with `sqlite3.OperationalError: unable to open database file` and restarted forever. Cause: Docker creates the missing `./data` folders as root, while the app runs as your user (`MSK_UID`), so it could not write. A second, hidden bug sat behind it: AI settings and chat history were written to the data root (`/data/ai_*.json`), which is not a mounted volume and not writable by the app user, so the first "save provider settings" returned 500 and the data would have been lost whenever the container was recreated. Fixes: a one-shot `prepare-data` service creates and chowns `data/app`, `data/projects` and `data/templates` before the app starts (also repairs folders left root-owned by an earlier failed start); AI files now live in `data/app/ai/` and files from the old location are moved in automatically; `data/templates` is a volume. Verified on a fresh clone, on a root-owned data folder, on a copy of the existing data, and across `docker compose down` + `up` (projects, templates, AI settings, agent edits and chat history all survived). Two regression tests cover the new location and the move. Not verified: a different `MSK_UID` than the host user's (the helper uses whatever `.env` says), and Docker on a platform other than this Linux host.

## 16. Later phases

**Phase 10: Dropbox.** Dropped together with Google Drive (see Phase 7). Nothing to build.

**Phase 11: offline writing (1-2 weeks, optional).**
1. Service worker caches the app shell and the open project's documents in IndexedDB.
2. Edits made offline go to a local queue, each with the base version it was edited from.
3. On reconnect, the queue replays with the Phase 2 version check; conflicts go to the same Keep mine / Keep theirs / Compare screen.
4. Clear indicators: offline badge, "saved on this device", "waiting to sync" counts.
5. Safety: never delete the local queue until the server confirms; export-unsynced-text button as a last resort.
6. iPhone limits (storage eviction, no background sync) are documented; Android gets background sync.

## 17. Testing strategy

| Layer | Tool | What |
|---|---|---|
| msklib | pytest, hypothesis | golden byte-identical round trips on 2 real projects; random unicode titles; mutation then desktop-Manuskript open check |
| Server | pytest + httpx | every endpoint, auth, CSRF, rate limits, concurrency, power-loss write test |
| AI | pytest; **fake SSE server NOT built yet** | Contract, auth, context and settings are tested. Provider payloads/stream parsers, cancel and error paths are not; a live smoke test against your llama server is still to do |
| Sync | pytest (`.lock` marker, 423 on write) | Exists. A real two-machine run is still to do (Phase 7) |
| Browser | Playwright | phone (390x844, touch) and desktop (1440x900): login, write, format, drag-reorder, AI chat, theme switch |
| Visual | Playwright screenshots | editor, cork, outline, AI sheet in all 32 themes; reviewed by you |
| Accessibility | axe-core + the contrast test | no serious violations, WCAG AA text contrast in every theme |
| Compatibility | headless desktop Manuskript | opens every project the web app saved |
| CI | GitHub Actions or a local script | lint, type check (ruff, mypy, svelte-check), all of the above on every commit |

## 18. Risks and how the plan handles them

| Risk | Mitigation |
|---|---|
| msklib writes something desktop Manuskript reads differently | golden and mutation tests against the real desktop app on every change to msklib; Phase 1 gate |
| Two devices edit at once | document versions, 409 on stale save, conflict prompt, sync conflict files, backups |
| An outside sync tool propagates a mass delete or two-way conflict | deletes go to `.trash/` inside each project (excluded from sync), the `.lock` marker pauses writes during a pass, stale saves get a 409; pick a one-way or one-editor-at-a-time setup and write it in docs/syncing.md. Two-way tools that make conflict copies are untested |
| Phone keyboard hides the toolbar | visualViewport docking tested on Android Chrome and iOS Safari |
| CodeMirror on mobile quirks (selection, IME) | test with real devices early in Phase 3; keep a plain-textarea fallback |
| Scope creep to full desktop parity | each phase has a Done-when gate; features not in this plan go to a backlog |
| Cloud AI bill surprise | rate limits, spend counter, clear per-provider indicator |
| GPL obligations | repo is GPL-3.0; keep the desktop fork's notices on copied files |
| Upstream Manuskript format changes | pin the supported format version; golden tests catch drift when you update the sample |

## 19. Timeline summary

| Milestone | Phases | Estimate (me coding, you testing each phase) |
|---|---|---|
| First usable version | 0 to 4 plus a light 9 | about 4 weeks |
| Near parity | 0 to 9 | about 10 to 12 weeks |
| Offline writing | 11 | +1 to 2 weeks |

Estimates assume one active phase at a time with a review gate between phases. Treat them as planning numbers, not promises; Phase 3 (editor on mobile) and Phase 7 (sync) are the likeliest to run over.

## 20. First steps when Phase 0 started (history)

1. Confirm the Proxmox VM spec (suggest 2 vCPU, 4 GB RAM, 40 GB disk, Debian 12) and which reverse proxy you use.
2. ~~Create the Google Cloud project early~~ (dropped, Phase 7).
3. ~~Host a one-page privacy policy for the Google consent screen~~ (dropped).
4. ~~Run the rclone spike~~ (dropped).
5. Then scaffold `server/` and `web/` and build Phase 0.
