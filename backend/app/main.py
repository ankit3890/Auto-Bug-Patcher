"""
AutoBug AI — FastAPI Application Entry Point
===============================================
Configures the FastAPI app with all routes, CORS, middleware, and startup events.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.config import router as config_router
from app.api.v1.issues import router as issues_router
from app.api.v1.patches import router as patches_router
from app.api.v1.repositories import router as repositories_router
from app.api.v1.search import router as search_router
from app.core.config import settings
from app.core.database import init_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("AutoBug AI — Starting up (env=%s)", settings.app_env)
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("AutoBug AI — Shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AutoBug AI",
    description="Autonomous bug detection, root cause analysis, and code fix generation",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app.include_router(repositories_router, prefix="/api/v1")
app.include_router(issues_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(patches_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health_check() -> dict[str, Any]:
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.app_env,
    }


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {"message": "AutoBug AI API", "docs": "/docs"}


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
