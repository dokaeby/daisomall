from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Settings, load_settings
from app.db import _should_use_postgres, connect, connect_postgres, init_db
from app.routers import admin, auth, cart, orders, shop
from app.web import render

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="다이소몰")
    app.state.settings = settings
    app.state.db_path = settings.database_path

    init_db(settings.database_path, settings.database_type)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    app.include_router(shop.router)
    app.include_router(auth.router)
    app.include_router(cart.router)
    app.include_router(orders.router)
    app.include_router(admin.router)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> Response:
        if exc.status_code in (403, 404):
            conn = _make_conn(app.state.db_path)
            try:
                return render(request, conn, f"{exc.status_code}.html", status_code=exc.status_code)
            finally:
                conn.close()
        return PlainTextResponse(str(exc.detail), status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> Response:
        logger.exception("처리되지 않은 오류: %s %s", request.method, request.url.path)
        conn = _make_conn(app.state.db_path)
        try:
            return render(request, conn, "500.html", status_code=500)
        finally:
            conn.close()

    return app


def _make_conn(path: Path | str) -> object:
    """Create a database connection (SQLite or PostgreSQL)."""
    if _should_use_postgres():
        return connect_postgres(str(path))
    return connect(path)
