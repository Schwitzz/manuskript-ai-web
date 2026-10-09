"""FastAPI app: API routers plus the built web app as static files."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.outline import router as outline_router
from app.api.plots_world import router as plots_world_router
from app.api.project_ops import router as project_ops_router
from app.api.projects import router as projects_router
from app.api.records import router as records_router
from app.api.search import router as search_router
from app.auth.router import router as auth_router
from app.config import get_settings
from app.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Manuskript AI", version="0.1.0", lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": app.version}

    app.include_router(auth_router)
    app.include_router(project_ops_router)
    app.include_router(projects_router)
    app.include_router(outline_router)
    app.include_router(records_router)
    app.include_router(plots_world_router)
    app.include_router(search_router)

    static = get_settings().static_dir
    if static and static.is_dir():
        app.mount("/_app", StaticFiles(directory=static / "_app"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                from fastapi import HTTPException
                raise HTTPException(404)
            candidate = (static / path).resolve()
            if path and candidate.is_file() and static.resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(static / "index.html")

    return app


app = create_app()
