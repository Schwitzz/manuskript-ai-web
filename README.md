# manuskript-ai-web

A self-hosted, single-user, phone-first web rewrite of the Manuskript AI fork:
write, organise and AI-assist a novel from any browser, with Google Drive sync.

**Status: planning.** No application code yet. Start with [PLAN.md](PLAN.md).

Licence: GPL-3.0 (see COPYING). Parts are derived from Manuskript
(https://github.com/olivierkes/manuskript) and the local AI fork.

## Development

```bash
# server (tests: 132)
cd server && uv sync && uv run pytest

# web app (type check, build, e2e at 390x844 and 1440x900)
cd web && npm install && npm run check && npm run build && npx playwright test

# run the built app locally
cd server && MSK_DATA_DIR=/tmp/msk-dev MSK_COOKIE_SECURE=false MSK_STATIC_DIR=../web/build uv run uvicorn app.main:app --port 8765

# Docker
cp .env.example .env   # set MSK_SECRET_KEY
docker compose up -d
```

Status: Phases 0 (login, Docker, PWA) and 1 (msklib) are done. Phase 2 (server API) is mostly done: see PLAN.md for the few items still open. Phase 3 (editor and app screens) is next. See docs/install.md.
Note: port 8000 is used by another service on the dev rig, so use `MSK_PORT=8770` in `.env` there.
