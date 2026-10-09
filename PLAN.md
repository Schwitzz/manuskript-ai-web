# manuskript-ai-web: build plan

A self-hosted, single-user, phone-first web rewrite of the Manuskript AI fork.
Status: PLAN ONLY. No application code exists yet. Review, then start Phase 0.

## 1. Decisions (locked)

| Topic | Decision |
|---|---|
| Repo | /home/ab/workspaces/manuskript-ai-web (new, GPL-3.0, reuses desktop-fork code) |
| Host | Proxmox VM (Debian 12 + Docker), 4 cores / 16 GB. Develop and test on the Ubuntu rig |
| Access | Home VPN + own reverse proxy + own domain. App speaks HTTP inside the LAN; the proxy does HTTPS |
| Users | One user, password login, optional TOTP two-factor |
| Cloud | Google Drive first, Dropbox later (Phase 10) |
| File format | MUST stay compatible with desktop Manuskript (same project folder, byte-identical round trip) |
| Offline writing | Deferred (Phase 11), after the web app is fully functional |
| Phone | Critical. Every screen is designed phone-first, then scaled up |
| AI | llama.cpp (Docker host 10.0.0.80:8180), OpenAI, Anthropic, Gemini, same four roles as the desktop fork |

## 2. Architecture

| Part | Choice | Why |
|---|---|---|
| Server | Python 3.12, FastAPI, uvicorn | Reuses the existing Python AI code; native SSE streaming |
| Project storage | Manuskript folder format on disk | Same files desktop Manuskript opens |
| App database | SQLite (WAL) | Users, sessions, settings, AI chat index, sync state |
| Browser app | SvelteKit + TypeScript, built as a static PWA | Fast on phones, installs to the home screen |
| Editor | CodeMirror 6 + live Markdown styling | Keeps text byte-exact (tabs, special spaces); rich-text editors rewrite Markdown |
| Icons | Lucide | Clean, consistent, icon-led toolbar |
| Touch drag and drop | SortableJS | Outline and corkboard reordering by touch |
| Cloud sync | rclone driven by the server | One tool for Google Drive now and Dropbox later |
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
      api/               projects, outline, documents, characters, plots, world, labels, settings, ai, sync, export
      ai/                providers.py context.py chats.py prompts.py
      sync/              rclone wrapper, conflict handling, snapshots
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
  docs/                  install.md google-drive.md reverse-proxy.md phone.md
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
3. Dockerfile (multi-stage): build web, then Python image serving API + static files. Installs pandoc, rclone, WeasyPrint libraries.
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

## 10. Phase 4: AI assistant (3-5 days)

Goal: parity with the desktop AI dock, plus streaming over the web.

1. Server: copy `ai/providers.py` unchanged (fixed cloud URLs, payload builders, stream parsers, model lists). Add `POST /api/ai/chat` returning SSE; client disconnect cancels the upstream request.
2. Provider settings page: provider, per-provider API key (write-only, encrypted), per-provider model drop-down filled from `/models`, cached; llama.cpp endpoint, context size, temperature, thinking (Off/low/med/high/xhigh) shown for llama.cpp only.
3. Roles: Co-author, Editor, Publisher, Reader with editable, resettable prompts.
4. Context builder: selection, then current scene, summary, POV character, book summary; per-source toggles; trimmed to the context window.
5. Chat UI: sheet on phone, right panel on desktop; provider/model/role pickers always visible and truly driving the request; "Reader says:" style labels stored per message; Enter sends (Shift+Enter newline, on desktop only; the phone keyboard uses a Send button).
6. Status line: thinking timer, prompt/output tokens (provider-reported usage with an estimate fallback), tokens per second, Cancel.
7. Chat history: stored server-side per project, auto-saved, Recent Chats list with open, New, Delete.
8. Extras on top of the desktop version: "Insert reply at cursor", "Replace selection", and a "Ask AI about selection" action in the editor selection menu.
9. Safety: a failed or cancelled prompt returns to the input box and is not added to history (the desktop bug fix).
10. Tests: provider payload and stream parser unit tests (reuse the desktop ones), a fake SSE server for end-to-end, and a live smoke test against your llama server.

Done when: all four providers stream into the chat, model switching mid-chat works, and history persists.

## 11. Phase 5: characters, plots, world, summary, general (about 1 week)

Goal: every non-editor data screen, phone friendly, writing the same files as desktop.

1. **Characters:** list with avatar colour/initials, search, importance; detail screen with the same fields and groups as desktop (name, motivation, goal, conflict, epiphany, summaries, notes, infos, importance, colour). Characters referenced by scenes (POV) are linked both ways.
2. **Plots:** plot list with importance; steps per plot with summaries; link characters and scenes; reorder steps by touch; a "resolution steps" section as in the file format.
3. **World:** OPML tree editor (add, nest, rename, move, delete) with a detail form (description, passion, conflict) and a search box.
4. **General and Summary screens:** book info (title, series, volume, genre, author, email, licence), the snowflake summary fields (situation, sentence, paragraph, page, full), word goal and progress.
5. **Labels and statuses:** manage names and colours; colour picker that works by touch.
6. **Inspector panel** next to the editor: metadata for the open scene (summary, POV, label, status, goal, notes) as a sheet on phone.
7. **Validation and empty states:** friendly empty screens, undo toast after delete (restores from `.trash/`).
8. Tests: each form writes the right file; round trip with desktop Manuskript headless; Playwright phone tests.

Done when: you can build characters and a plot on your phone and see the same data in desktop Manuskript.

## 12. Phase 6: corkboard, outline table, storyline (1-1.5 weeks)

Goal: the visual views, usable by touch.

1. **Corkboard:** cards from the current folder; title, summary, label colour stripe, status chip, word count; themed (dark cards in dark schemes, with a paper-card option); card size slider; background colour setting.
2. **Touch drag and drop** with SortableJS: long-press to lift, auto-scroll at screen edges, drop between cards or into a folder; works with mouse and touch.
3. **Outline table:** sortable columns (title, label, status, POV, words, goal, compile), column picker, inline editing; on phone it collapses to stacked rows with the key fields.
4. **Folder views** (text, cork, outline) switchable per folder, remembered in project settings like desktop.
5. **Storyline:** plots as lanes against the scene sequence with character and plot-step markers; pan and pinch-zoom; tap to open a scene.
6. **Bulk actions:** select several items (long-press) to set label, status, compile flag, or move.
7. Performance: virtualised lists so a 2,000-scene project stays smooth on a mid-range phone.
8. Tests: reorder persists to files and renames them like desktop; visual snapshots in all themes; touch emulation in Playwright.

Done when: you can reorganise chapters by touch and desktop Manuskript shows the new order.

## 13. Phase 7: Google Drive two-way sync (4-6 days)

Goal: each project mirrors to a Drive folder, both ways, without ever silently losing text.

### 13.1 One-time Google setup (documented in docs/google-drive.md)
1. Create a Google Cloud project and enable the Drive API.
2. OAuth consent screen: user type External. **Publishing status must be "In production".** Confirmed in several sources: an External app in Testing gets refresh tokens that expire after 7 days (dev.to write-up quoting Google's OAuth docs; developers.google.com/health/setup; a Google Ads API forum advisor at groups.google.com/g/adwords-api/c/Z_kihrf6VCE). Re-authenticating in Testing only buys another 7 days (dev.to).
3. Once published ("In Production"), refresh tokens generally do not expire unless revoked or unused for a prolonged period, typically six months (developers.google.com/health/setup). Other expiry causes listed by third parties quoting Google's docs: user revocation, and a limit of 100 live refresh tokens per Google Account per OAuth client ID, after which the oldest is invalidated without warning (unified.to). So: sync at least occasionally, and never loop on re-authentication. My own precaution, NOT from a source: after publishing, disconnect and reconnect Drive once so the app holds a token issued under the production status.
4. Publishing can have prerequisites. One developer's write-up (dev.to, not an official source) says the Publish button was greyed out until branding fields were filled in: an application homepage URL and a privacy policy URL are named, and the excerpt I saw cuts off before the rest. A 2023 blog (newscrewdriver.com) reports that clicking Publish for an app with sensitive scopes asked for verification: privacy policy link, a demo video, a written justification and all domains verified in Search Console. Plan on needing a domain you control and a public privacy page. Not confirmed for your account or for the `drive` scope.
5. Scope choice. Confirmed on developers.google.com/drive/api/guides/api-specific-auth (page last updated 2026-09-03): `https://www.googleapis.com/auth/drive` ("View and manage all your Drive files") is listed under RESTRICTED scopes; `drive.file` is listed as non-sensitive and grants per-file access to files the app creates, or that the user opens or shares with it through the Google Picker API or the app's file picker; the page recommends migrating to non-sensitive scopes where possible. So full `drive` is the only scope that would let the server see files desktop Manuskript writes through another sync client, and it is the one Google restricts.
6. Verification. Confirmed: Google's help page "When is verification not needed" (support.google.com/cloud/answer/13464323, fetched) says a personal-use app (fewer than 100 users) can continue without going through verification, users click through the "unverified app" warning, and the "production" tier project should have the published status "In Production"; apps in testing mode are also not subject to verification but keep the unverified screen and the 100-user cap. The Drive scopes page (fetched) adds: restricted-scope data stored on servers requires a security assessment, and only specific app types may use restricted Drive scopes (backup and sync, productivity and education, reporting and security). A personal single-user sync app plausibly fits "backup and sync", but that is my reading, not Google's statement. The restricted-scope verification page (not re-fetched in this step) says assessments recur at least every 12 months, and Google's FAQ (support.google.com/cloud/answer/13463817) puts verification at about 6 weeks. Not confirmed: whether the console lets you publish a personal project with `drive` without forcing verification. Fallback if it forces it: use `drive.file` plus the Google Picker (you pick the project folders once; the app sees only those items), and keep desktop Manuskript syncing through the web app's export or its own rclone job rather than through Drive's files directly.
7. OAuth client type: Web application, redirect URI `https://<your-domain>/api/sync/google/callback` (only your browser has to reach it, so the VPN is fine). NOT checked in this research; from memory.

### 13.2 Design
- The server runs `rclone bisync` between `/data/projects/<Project>` and `Drive:Manuskript/<Project>`. rclone remote and token are created through the app's own OAuth flow; the config file is 0600 and its secrets are encrypted (confirm rclone's config-password support in the first spike).
- Per-project on/off toggle and a Drive folder picker (list folders through the Drive API).
- Triggers: 30 seconds after the last save, every few minutes, on app start, and a "Sync now" button. One pass at a time per project (rclone's lock file plus our own lock).
- Exclusions: `.trash/`, `.lock`, `*.tmp`, sync state, and Google Docs (`--drive-skip-gdocs`).
- All writes by the server are atomic (temp file then rename) so a pass never sees half a file.

### 13.3 Safety rules (non-negotiable)
1. **Explicit flags only.** Read from the rclone.org/bisync page on 8 Oct 2026: `--max-delete PERCENT` (safety check on the maximum percentage of deleted files; the run aborts if exceeded; default 50%), `--force` (bypasses the max-delete check), `--check-access` with `--check-filename` (default RCLONE_TEST), `--check-sync` (true|false|only), `--compare` (default size,modtime), `--conflict-resolve` (default none: keep and rename both files), `--conflict-loser` (default num: append a number to the conflict suffix), `--conflict-suffix`, `--resilient` (retry after less-serious errors instead of requiring --resync), `--recover` (recover from interruptions without --resync), `--max-lock` (expire old lock files; default never; minimum 2m), `--backup-dir1` and `--backup-dir2`, `--resync` / `--resync-mode`, `--ignore-listing-checksum`. The page's own example also uses `--drive-skip-gdocs`. Flag spellings change between releases, so the first step of the phase is still a spike that runs `rclone bisync --help` on the pinned version.
2. **Conflicts never overwrite.** With the documented defaults (`--conflict-resolve none`, `--conflict-loser num`) nothing is auto-resolved and the conflicting files are renamed with a numeric suffix. Confirm in the spike, then list them in the app with Compare, Keep mine, Keep theirs.
3. **Delete limit.** Use `--max-delete` with a LOW percentage. The docs say it is a percentage with a default of 50%, and the run aborts when it is exceeded; the safety-measures section says this protects against a failed listing being read as all files deleted. `--force` bypasses the check, so the app never passes `--force` by itself. A 50% default is too loose for a book project, so choose a small value in the spike (small projects with few files may need an absolute-count guard of our own as well). Desktop Manuskript can delete and rewrite a whole project folder on save, and bisync propagates deletions both ways, so this matters.
4. **Backup dirs.** Every pass keeps overwritten and deleted files in a dated backup folder outside the synced tree on both sides (`--backup-dir1/2`), pruned after a retention period.
5. **Access check.** `RCLONE_TEST` marker files so a missing or empty mount can never look like a mass delete.
6. **First connect is a guided, previewed step.** `--resync` makes one side win. The app shows a dry run and asks: Drive wins, this server wins, or merge keeping both. Never automatic.
7. **Resync repair never runs by itself.** If bisync reports it needs a resync, the app shows the same guided choice.

### 13.4 After each pass
- Diff the changed files, reload them through msklib, bump document versions, emit an SSE event.
- A document with unsaved edits in an open tab that also changed remotely shows the version-conflict prompt from Phase 3.
- Status panel: last sync time, files changed, conflicts, errors, and a log viewer.

### 13.5 Failure handling
- `invalid_grant` or revoked access: banner "Reconnect Google Drive" with a one-click re-auth; writing is never blocked.
- Network down: exponential backoff, a clear offline badge, no data loss.
- Rate limiting: back off and retry, and use our own OAuth client ID rather than a shared one.
- Refresh-token hygiene: keep one token per client ID in use; Google reportedly invalidates the oldest of 100 per account and client ID (unified.to quoting Google's docs), so the app never re-authenticates in a loop.

### 13.6 Your Ubuntu desktop
- Google does not ship an official Drive desktop client for Linux (from my own knowledge, not checked in this research), so desktop Manuskript needs its own sync. Provide docs/desktop-sync.md with an `rclone bisync` systemd timer using the same safety flags, or mount Drive through GNOME Online Accounts.
- Rule of thumb: let one device be the editor at a time; the safety rules above cover accidents.

### 13.7 Tests
- Two local folders as fake remotes (rclone's local backend): edit both sides, delete one side, mass delete, empty remote, interrupted pass, lock contention.
- Mocked 400 `invalid_grant` shows the reconnect banner.
- A live round trip against a throwaway Drive folder with your account.
- Check that desktop Manuskript opens a project after it has travelled through Drive and back.

Done when: an edit on the phone reaches the Ubuntu desktop and back, a forced conflict leaves both versions, and a simulated mass delete is stopped.

### 13.8 Open questions to settle in the spike
- Exact flag spellings and defaults for the rclone version we ship (pin it in the Dockerfile), and a sensible `--max-delete` percentage for projects with few files.
- Whether a `--backup-dir1/2` layout works with Drive. The rclone page shows them as per-side directories and warns that deleted files from both paths would mix if one shared `--backup-dir` is used; I did not confirm any further rule about overlap.
- How rclone stores the Drive token (config-file encryption) and whether the app can supply it at run time instead of a file.
- `drive` (full scope, restricted, personal-use exemption, possible forced verification on publish) versus `drive.file` (per-file via the Picker, non-sensitive, cannot see desktop-written files). Decide first; it shapes the whole of Phase 7.
- Whether Publish is blocked, or pushes you into verification, for your project with the `drive` scope.
- Whether a published, unverified, personal-use app keeps its refresh token alive in practice. Documents say yes; weeks of real use will confirm. The reconnect banner is the safety net.

### 13.9 Sources retrieved on 8 Oct 2026 (and what was NOT)
Retrieved and read:
- developers.google.com/health/setup: 7-day expiry in Testing; generally no expiry once In Production unless revoked or unused for about six months.
- dev.to/ko-hi/googles-oauth-testing-mode-expires-refresh-tokens-in-7-days-publish-the-consent-screen-before-24hm: 7-day rule quoting Google's docs; re-authenticating only buys 7 days; Publish button greyed out until branding fields are filled (not an official source).
- groups.google.com/g/adwords-api/c/Z_kihrf6VCE: Google Ads API forum advisor says to change the status to In production.
- unified.to/blog/why_google_oauth_returns, unipile.com, cdata.com: third-party summaries of Google's expiry conditions, including the 100-token cap and six-month inactivity (third party, quoting Google).
- newscrewdriver.com/2023/02/04/google-oauth-test-tokens-expire-weekly: Publish prompting verification for sensitive scopes (2023, one user).
- support.google.com/cloud/answer/13464323 (fetched directly): personal use, fewer than 100 users, no verification, "In Production", unverified-app screen and the 100-user cap in testing.
- developers.google.com/drive/api/guides/api-specific-auth (fetched directly, updated 2026-09-03): `drive` is restricted, `drive.file` is non-sensitive and per-file, restricted-scope app categories, security assessment for server-side storage.
- support.google.com/cloud/answer/13463817: verification types and timings (restricted scope about 6 weeks, security assessment).
- developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification: exceptions include personal use; server-side storage needs a security assessment; recurring every 12 months.
- rclone.org/bisync (fetched and read directly): flags and defaults, safety measures, Dropbox filter examples in its table of contents.
NOT retrieved, from memory: the OAuth client type and redirect URI in 13.1 item 7; that Google ships no official Linux Drive client (13.6); how rclone stores or encrypts the Drive token; whether publishing with `drive` forces verification for a personal project.

## 14. Phase 8: export, import, search, goals, revisions (about 1 week)

1. **Export (server side, pandoc):** Markdown, plain text, HTML, DOCX, ODT, EPUB, and PDF (HTML to PDF with WeasyPrint, so no LaTeX install is needed). Choose which items to include (the compile flags), separators, title page, and a simple style choice. Preview in the browser before download; large exports run as a background job with progress.
2. **Desktop compile parity:** the same compile flags, scene separators and the Manuskript "basic" outputs, tested by comparing against desktop output for the sample project.
3. **Import:** Markdown or plain-text files and folders, OPML, DOCX/ODT/EPUB through pandoc, and zipped `.msk` projects. Split by headings into folders and scenes, with a dry-run preview.
4. **Search:** project-wide full text (file scan, see Phase 2 item 7) across scenes, notes, characters, plots, world, with a results list that jumps to the match; command palette (Ctrl+K and a search icon on phone) for jumping to items and running actions.
5. **Word-count goals:** per-scene and per-project goals, a daily goal with a progress ring, streak, and a small history chart stored in SQLite. Counts follow the same rules as desktop (count spaces setting).
6. **Revisions:** list a scene's saved revisions, view a diff against the current text, restore with one tap (restoring itself creates a revision).
7. **Frequency analyser and spell language:** word-frequency view; dictionary language per project; custom dictionary.
8. Tests: export a golden project and compare text content; import then export round trip; FTS rebuild after external file changes.

Done when: a DOCX and an EPUB export open correctly, import of a Markdown manuscript works, and search finds text across the project.

## 15. Phase 9: hardening, backups, install guide (about 1 week)

1. **Security review:** run an automated dependency audit; secure headers (CSP, HSTS via the proxy, no sniffing, frame denial); upload size and type limits; path-traversal tests on every file API; zip-slip tests on import and upload; SSRF guard on the llama endpoint field (only allow addresses you configure).
2. **Rate limits** on login, AI calls (so a stuck page cannot run up a cloud bill), exports and sync triggers. A monthly AI-spend counter per provider on the settings page.
3. **Backups:** nightly snapshot of `/data/projects` and the SQLite database to a separate volume, with restore tested; retention settings; one-click "download everything" zip.
4. **Logging and health:** structured logs with secrets stripped, `/api/health` and `/api/ready`, a status page showing sync, disk and the last backup.
5. **Updates:** versioned database migrations that run on start; refuse to start on a newer-than-known database; a documented upgrade and rollback.
6. **Docs:** docs/install.md (Proxmox VM, Docker), docs/reverse-proxy.md (Caddy, nginx and Nginx Proxy Manager examples with WebSocket/SSE-friendly settings, no response buffering for the AI stream), docs/google-drive.md, docs/phone.md (install to home screen, Android and iPhone notes), docs/backup-restore.md.
7. **Performance pass:** large-project load test (2,000 scenes, 500,000 words) on phone emulation; lazy-load the editor, charts and export UI; bundle-size budget.
8. **A week of real use** on your own manuscript before calling it done; fix the daily annoyances.

Done when: restore from backup is proven, the security checklist is clean, and the guides get a fresh VM to a working login.

## 16. Later phases

**Phase 10: Dropbox (about 1 day).** Same rclone bisync engine with a Dropbox remote. The rclone bisync page itself includes Dropbox filter examples, so there is support for it. Add a provider switch in the sync settings and a docs/dropbox.md. Reuses all Phase 7 safety rules.

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
| AI | pytest + fake SSE server | all four providers' payloads and stream parsers, cancel, error paths; plus a live smoke test against your llama server |
| Sync | pytest + local rclone remotes | conflicts, mass delete stopped, interrupted pass, lock contention |
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
| Mass delete from desktop rewrite propagating through Drive | `--max-delete`, backup dirs, check-access file, snapshots before big remote changes, guided first sync |
| Google refresh token expires | publish the app, reconnect banner, token-age display, sync at least weekly |
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
| Dropbox | 10 | +1 day |
| Offline writing | 11 | +1 to 2 weeks |

Estimates assume one active phase at a time with a review gate between phases. Treat them as planning numbers, not promises; Phase 3 (editor on mobile) and Phase 7 (sync) are the likeliest to run over.

## 20. First steps when Phase 0 starts

1. Confirm the Proxmox VM spec (suggest 2 vCPU, 4 GB RAM, 40 GB disk, Debian 12) and which reverse proxy you use.
2. Create the Google Cloud project early (the publishing and domain steps in 13.1 can take days to clear).
3. Host a one-page privacy policy on your domain for the Google consent screen.
4. Run the rclone spike from 13.8 on your Ubuntu rig before writing sync code.
5. Then scaffold `server/` and `web/` and build Phase 0.
