"""FastAPI application entry point.

In production the built frontend static files are served by this app (one container, ADR-10);
in development the API runs on its own and the frontend dev server proxies to it.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.feedback import router as feedback_router
from app.api.me import router as me_router
from app.api.metrics import router as metrics_router
from app.core.config import settings
from app.core.middleware import security_headers

settings.validate_production()  # refuse the dev session secret when REQUIRE_STRONG_SECRET=true

app = FastAPI(title="HR Assistant", version=__version__)

app.middleware("http")(security_headers)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(metrics_router)
app.include_router(feedback_router)
app.include_router(admin_router)
app.include_router(me_router)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    # Version lets the status page confirm which build is live in the demo.
    return {"status": "ok", "version": __version__}


# Serve the built frontend (one container, ADR-10). The SPA's client-side routing means any
# non-API path returns index.html. Mounted last so it never shadows the API routes above.
# `html=True` makes StaticFiles fall back to index.html for unknown paths.
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
