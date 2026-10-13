# manuskript-ai-web

A self-hosted, single-user, phone-first web rewrite of the Manuskript AI fork:
write, organise and AI-assist a novel from any browser. Projects are plain Manuskript
folders, so desktop Manuskript opens the same files.

**Status: active development.** See [PLAN.md](PLAN.md) for the build plan.

Licence: GPL-3.0 (see COPYING). Parts are derived from Manuskript
(https://github.com/olivierkes/manuskript) and the local AI fork.

## Development

```bash
# server (tests: 316)
cd server && uv sync && uv run pytest

# web app (type check, build, e2e at 390x844 and 1440x900)
cd web && npm install && npm run check && npm run build && npx playwright test

# run the built app locally
cd server && MSK_DATA_DIR=/tmp/msk-dev MSK_COOKIE_SECURE=false MSK_STATIC_DIR=../web/build uv run uvicorn app.main:app --port 8765

# Docker
cp .env.example .env   # set MSK_SECRET_KEY
docker compose up -d
```

Status: writing, outline, cards, storyboard (flow diagram), characters, plots, world, labels,
project templates and the AI assistant are built. Not built: export, import,
search/revisions screens, drag-and-drop, storyline, backups, offline mode. There is no cloud
sync; sync the project folders with a tool of your choice. The AI assistant has been run live
against a llama.cpp server; the cloud providers (OpenAI, Anthropic, Gemini) have tests but have
not been tried with real accounts.
See [PLAN.md](PLAN.md) for the details and the next steps.

Note: port 8000 is used by another service on the dev rig, so use `MSK_PORT=8770` in `.env` there.
