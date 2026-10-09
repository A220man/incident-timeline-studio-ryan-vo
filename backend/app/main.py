"""Incident Timeline Studio API factory with explicit lifetime and configuration."""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .core.config import Settings, load_settings, validate_settings, ensure_db_dir
from .core.db import Database
from .core.auth import router as auth_router, OIDCClient
from .core.errors import AppError
from .api.routes import router


def create_app(settings: Settings | None = None, oidc_transport=None) -> FastAPI:
    settings = settings or load_settings()
    validate_settings(settings)
    ensure_db_dir(settings.database_path)
    db = Database(settings.database_path)

    @asynccontextmanager
    async def lifespan(app):
        yield
        db.close()

    app = FastAPI(title='Incident Timeline Studio', version='1.0.0', lifespan=lifespan)
    app.state.settings = settings
    app.state.db = db
    app.state.oidc = OIDCClient(settings, oidc_transport)
    app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_url], allow_credentials=True,
                       allow_methods=['GET', 'POST', 'PATCH', 'DELETE'], allow_headers=['Content-Type', 'X-CSRF-Token'])

    @app.exception_handler(AppError)
    async def expected_error(request: Request, error: AppError):
        return JSONResponse({'error': {'code': error.code, 'message': error.message}}, status_code=error.status)

    @app.middleware('http')
    async def safe_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/api/health')
    def health():
        db.query_one('SELECT 1')
        return {'status': 'ok', 'version': '1.0.0'}

    app.include_router(auth_router)
    app.include_router(router)
    return app
