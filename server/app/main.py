import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import engine

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Mood Sync API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/")
def serve_frontend_root() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend build output is missing.")
    return FileResponse(index_path)


@app.on_event("startup")
def ensure_database_columns() -> None:
    try:
        init_db()
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS message TEXT"))
            connection.execute(text("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS selected_vibes JSONB DEFAULT '[]'::jsonb"))
            connection.execute(text("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS context_snapshot JSONB DEFAULT '{}'::jsonb"))
            connection.execute(text("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS rag_context TEXT"))
            connection.execute(text("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS llm_context TEXT"))
            connection.execute(text("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS generation_profile JSONB DEFAULT '{}'::jsonb"))
            connection.execute(text("ALTER TABLE favorites ADD COLUMN IF NOT EXISTS album_name VARCHAR(255)"))
            connection.execute(text("ALTER TABLE favorites ADD COLUMN IF NOT EXISTS album_image_url VARCHAR(1024)"))
            connection.execute(text("ALTER TABLE favorites ADD COLUMN IF NOT EXISTS spotify_url VARCHAR(1024)"))
            connection.execute(text("ALTER TABLE favorites ADD COLUMN IF NOT EXISTS duration_ms INTEGER"))
            connection.execute(text("ALTER TABLE favorites ADD COLUMN IF NOT EXISTS mood VARCHAR(64)"))
            connection.execute(text("ALTER TABLE favorites ADD COLUMN IF NOT EXISTS reason VARCHAR(1000)"))
    except OperationalError as exc:
        logger.warning("Skipping startup DB column bootstrap because the database is unavailable: %s", exc)


@app.get("/api/health")
def health_check() -> dict[str, bool | str]:
    return {"ok": True, "message": "Mood Sync FastAPI server is running."}


@app.get("/{full_path:path}")
def serve_frontend_spa(full_path: str) -> FileResponse:
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found.")

    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend build output is missing.")
    return FileResponse(index_path)
