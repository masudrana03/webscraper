"""Serve the React web UI build as static files from FastAPI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

UI_DIST = Path(__file__).parent.parent / "web-ui" / "dist"


def mount_ui(app: FastAPI):
    """Mount the React SPA at root. Call after all API routes are defined."""
    if not UI_DIST.exists():
        print(f"Warning: UI build not found at {UI_DIST}. Skipping UI mount.")
        return

    app.mount("/assets", StaticFiles(directory=str(UI_DIST / "assets")), name="ui-assets")

    @app.get("/{path:path}")
    async def ui_catchall(path: str):
        """Serve the SPA index.html for all non-API routes (client-side routing)."""
        return FileResponse(str(UI_DIST / "index.html"))

    @app.get("/")
    async def ui_index():
        return FileResponse(str(UI_DIST / "index.html"))
