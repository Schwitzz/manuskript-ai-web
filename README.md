# Moduskript Web (`manuskript-ai-web`)

A self-hosted, phone-first and desktop-friendly web writing studio built with **FastAPI (`msklib`)** and **SvelteKit 5**.

**Moduskript Web** operates directly on plain **Moduskript / Manuskript project folders** (`<Project>/MANUSKRIPT` + `<Project>.msk`) with a byte-identical round trip, commingling its file structure with the **Moduskript Desktop App** ([Schwitzz/Moduskript](https://github.com/Schwitzz/Moduskript)) so you can switch between Desktop and Web at any time.

---

## Features

- **Write Editor (`/write`)**:
  - CodeMirror 6 Markdown editor with byte-exact preservation of tabs, non-breaking spaces, and line endings.
  - **Readable vs. MD Code Toggle**: Switch live between **MD Code** (raw Markdown syntax visible) and **Readable Mode** (hides `#`, `**`, `*`, `~~`, `>`, `` ` `` syntax markers on inactive lines while styling headings, bold, italic, strikethrough, code, and blockquotes; reveals raw syntax on the active cursor line).
  - Formatting toolbar, autosave with conflict detection (`409` stale-save protection), session word-count goal ring, typewriter scrolling, line focus mode, spellcheck toggle, and side **Inspector** + **AI Chat** drawers.
- **Outline (`/outline`)**:
  - **Tree View** and **Table View** with `SortableJS` drag-and-drop reordering in both views.
  - **Chapters & Indented Scenes**: Create Folders, Chapters (`.md` documents labeled `Chapter`), and Scenes (automatically placed and visually indented beneath their Chapter).
  - **Associated Notes**: Attach, edit, and delete multiple titled notes (`associatedNotes`) on Chapters, Scenes, and Folders.
- **Multi-Board Whiteboard (`/whiteboard`)**:
  - Persisted in `<project>/whiteboards.json` via `GET/PUT /api/projects/{name}/whiteboards` (shared with the Desktop App's native Whiteboard).
  - **Multiple Whiteboards per Project**: Create, switch, rename, and delete named boards from the centered toolbar.
  - **Shapes & Sticky Notes**: Rectangle, Circle, Triangle, Arrow, and Note nodes with double-click inline renaming, toolbar label/note inspector, unobtrusive hover note popovers, and a **Show notes** toggle.
  - **4 Line Styles & Custom Colors**: Connect nodes using `Solid`, `Dash`, `Dot`, or `Solid dashed` lines, and color any shape, note, or connector line using the 11-color palette or custom color picker.
- **Story Bible (`/characters`, `/plots`, `/world`, `/labels`, `/settings`)**:
  - Full CRUD for Characters (with avatars, motivation/goal/conflict/epiphany, custom infos, undo-delete), Plots (with resolution steps), World hierarchy (`world.opml`), Labels & Statuses, Book Info, and Snowflake Summaries.
- **Project Templates (`/more`)**:
  - Save any project's structure as a reusable template and create new projects from it.
- **Streaming AI Assistant (`/more/ai` & Write Drawer)**:
  - Supports local `llama.cpp` servers and cloud providers (OpenAI, Anthropic, Gemini) with SSE streaming, thinking-token support, 4 editable role personas (*Co-author*, *Editor*, *Publisher*, *Reader*), and automatic scene/POV/book context injection.
- **32 WCAG-Checked Themes**:
  - All 31 Desktop colour schemes + *System*, switchable live in CSS variables.
- **Security**:
  - Argon2id password authentication, optional TOTP 2FA with 10 recovery codes, CSRF protection, login rate limiting, and route-table authentication enforcement.

---

## Running with the Desktop App (Commingled Mode)

When launched from the **Moduskript Desktop App** (*Tools → Launch Web App in Browser* or *Settings → Web Server & Sync*):
- Both apps share `/home/ab/workspaces/manuskript-ai-web/data/projects`.
- Can be configured in Desktop Settings to **start automatically on launch** and **keep running in the background when the desktop app is closed**.

---

## Standalone Development & Docker

```bash
# 1. Run Server Tests (313 pytest tests)
cd server && uv sync && uv run pytest

# 2. Run Web Type Check, Unit Tests (144 vitest), Build & E2E Tests (18 Playwright tests at 390x844 & 1440x900)
cd web && npm install && npm run check && npm test && npm run build && npx playwright test

# 3. Run Locally (Port 8770)
cd server && MSK_DATA_DIR=../data MSK_COOKIE_SECURE=false MSK_STATIC_DIR=../web/build uv run uvicorn app.main:app --port 8770

# 4. Run with Docker Compose
cp .env.example .env   # set MSK_SECRET_KEY
docker compose up -d
```

---

## Recent Iteration 2 Enhancements (Resolved)

1. **Commingled Folder Selection & Live Server Path**: Selecting any project folder in Desktop Settings (`Settings → Web Server & Sync`) resolves the project directory, syncs `.msk` ↔ `MANUSKRIPT` markers, passes `MSK_PROJECTS_DIR_OVERRIDE` to the server, and restarts the background server automatically.
2. **Desktop Modern Lucide SVG Icon Overhaul**: Added `manuskript/ui/modernIcons.py` providing theme-adaptive Lucide vector icons across the Desktop navigation rail (including the **Board** tab), Editor `FormatBar`, Whiteboard toolbar, Settings sidebar, and AI Chat dock.
3. **Resilient Initial Login & Account Creation (`/login`)**: Guaranteed SQLite initialization and added a tabbed **Sign In / Create Account** UI on `/login`.
4. **Web App `/more` Workspace Hub & Full Parity for Title Properties, World Builder & Plots**:
   - Redesigned `/more` into a structured Story & Manuscript Workspace hub.
   - Upgraded **Title Properties & Snowflake Summary** (`/settings`) with canonical `infos.txt`/`summary.txt` keys and live word/page counts.
   - Upgraded **World Builder** (`/world`) with a split OPML tree, search filter, and guided world-building prompt templates.
   - Upgraded **Plots** (`/plots`) with a master-detail view, linked character badges, and plot structure step templates (*Freytag's Pyramid*, *Three Acts*, *Hero's Journey*, *Dan Wells 7-Point*).
5. **Desktop Editor & Whiteboard UX**: Single-row icon-led `FormatBar` with Typography popover, icon-led Whiteboard toolbar, and direct **click-and-drag line connections from node handles**.
6. **Desktop AI Chat Header**: Removed the native `QDockWidget` title bar (`×` / tiny float button) and replaced all controls with modern icons.

## Version `0.01.1` — UI Bug Fixes & Improvements
- **Readable Mode & True Formatting Toggles**: Icon-only Readable Mode toggle that hides Markdown syntax across all lines (including the active cursor line) and unwraps existing `**`, `*`, `~~`, `# `, `> `, `- `, `1. ` markers when toggled off.
- **Categorized Write Toolbar, Static Viewport & Docked Resizable AI Chat**:
  - Labeled toolbar categories (**Formatting**, **Assistant**, **Info**), fixed viewport layout where only the typing area scrolls, comfortable centered reading width, togglable left **Project Outline** sidebar, top **Chapters / Scenes / Notes dropdown**, and side-by-side **resizable AI Chat panel**.
- **Shared AI Sync & Default Model Selector**: Unified AI provider settings and chat histories (`chats.db`) across Web and Desktop, with a Default Model selector + custom model ID input + Fetch Models button per provider in `/more/ai`.
- **Organized `/more` Hub, `/themes` Window, `ProjectNav` & Full User Management**:
  - Organized `/more` into **Project**, **Appearance** (opens `/themes` with 32 colour schemes + Spellcheck/Inspector/Word Count toggles), **Assistant**, and **Users**.
  - Added unified `ProjectNav` across Title Properties, Summary, Plot & Subplots, Characters, World Builder, and Labels & Statuses.
  - Full **Users** management (add user, modify password, remove user) in both Web (`/register`) and Desktop (`Settings → Web Server & Sync`).

---

## License
GNU General Public License v3.0 (`COPYING`).
