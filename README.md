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

## Known Issues & Upcoming Refinements (Next Iteration)

1. **Commingled Folder Selection & Live Server Path**: Choosing a project folder in Desktop Settings and clicking Sync can point to the folder itself rather than `MSK_DATA_DIR/projects` or leave an already-running background web server pointing at the old `MSK_DATA_DIR`.
2. **Desktop Board Tab Icon**: Needs a dedicated modern icon in the Desktop left navigation rail.
3. **Initial Account Creation / Login Flow**: Creating a new login on `/login` can crash or fail under certain session/cookie states; the initial setup and login flow is being reworked.
4. **Desktop Modern Icon Overhaul**: Sourced modern SVG icons (Lucide) are being installed across the entire Desktop UI.
5. **Web App "More" Menu UI Overhaul**: Redesigning `/more` to mirror the Desktop App's workspace structure and navigation.
6. **Web App Parity for Title Properties, World Builder & Plots**: Bringing Title/Book Info & Snowflake Summary, World Builder (`world.opml`), and Plots (`plots.xml` with steps & linked characters) to full visual and functional parity with the Desktop App.
7. **Desktop Writer/Editor Icon Toolbar**: Transitioning the Desktop Editor `FormatBar` from text labels to an icon-led toolbar matching the Web Editor.
8. **Desktop Whiteboard UX & Handle Drag-to-Connect**: Moving the Desktop Whiteboard toolbar to icon buttons and enabling direct click-and-drag line drawing from node handles.
9. **Desktop AI Chat Header & Icon Controls**: Removing the native `QDockWidget` title bar (`×` / tiny float button) and replacing text buttons (`New`, `Del`, `Dock/Undock`) with modern icons across the AI Chat and all other panels.

---

## License
GNU General Public License v3.0 (`COPYING`).
