from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .config import CORS_ORIGINS
from .database import engine
from .models import Base
from .routers import auth, constraints, demands, fixed_assignments, groups, imports, members, pattern_rules, patterns, personal, rest_requests, schedules
from .services.tasks import run_periodic_tasks

STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    task = asyncio.create_task(run_periodic_tasks())
    yield
    task.cancel()
    await engine.dispose()


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response


app = FastAPI(
    title="Shift Scheduler API",
    version="0.2.0",
    description="自動排班システム API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(NoCacheMiddleware)

app.include_router(auth.router)
app.include_router(members.router)
app.include_router(patterns.router)
app.include_router(schedules.router)
app.include_router(demands.router)
app.include_router(constraints.router)
app.include_router(fixed_assignments.router)
app.include_router(groups.router)
app.include_router(imports.router)
app.include_router(rest_requests.router)
app.include_router(personal.router)
app.include_router(pattern_rules.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/tasks/auto-close-rest-requests")
async def trigger_auto_close():
    from .database import async_session
    from .services.tasks import auto_close_expired_rest_requests
    async with async_session() as db:
        result = await auto_close_expired_rest_requests(db)
    return result


@app.post("/api/tasks/cleanup-old-data")
async def trigger_cleanup():
    from .database import async_session
    from .services.tasks import cleanup_old_schedule_data
    async with async_session() as db:
        result = await cleanup_old_schedule_data(db)
    return result


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = STATIC_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))
