"""
NIFTY 100 Financial Intelligence Platform
FastAPI Application

Day 38 — API Scaffold
"""

from pathlib import Path
from datetime import datetime, timezone
import sqlite3
import time
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import (
    companies,
    screener,
    sectors,
    peers,
    valuation,
    portfolio,
    documents,
    health,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "nifty100.db"

API_VERSION = "1.0.0"

START_TIME = time.time()


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "nifty100_api"
)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="NIFTY 100 Financial Intelligence Platform API",
    description=(
        "REST API for the NIFTY 100 Financial Intelligence Platform. "
        "Provides company, screening, sector, peer, valuation, "
        "portfolio, document and health endpoints."
    ),
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST LOGGING
# ============================================================

@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next,
):
    """Log every API request and its response time."""

    start = time.time()

    response = await call_next(request)

    duration_ms = (
        time.time() - start
    ) * 1000

    logger.info(
        "%s %s -> %s (%.2f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    """API root endpoint."""

    return {
        "name": "NIFTY 100 Financial Intelligence Platform API",
        "version": API_VERSION,
        "status": "online",
        "docs": "/docs",
        "api_prefix": "/api/v1",
    }


# ============================================================
# API INFO
# ============================================================

@app.get("/api/v1")
def api_info():
    """Return API information."""

    return {
        "name": "NIFTY 100 Financial Intelligence Platform API",
        "version": API_VERSION,
        "status": "online",
        "prefix": "/api/v1",
        "docs": "/docs",
    }


# ============================================================
# ROUTERS
# ============================================================

app.include_router(
    companies.router,
    prefix="/api/v1",
)

app.include_router(
    screener.router,
    prefix="/api/v1",
)

app.include_router(
    sectors.router,
    prefix="/api/v1",
)

app.include_router(
    peers.router,
    prefix="/api/v1",
)

app.include_router(
    valuation.router,
    prefix="/api/v1",
)

app.include_router(
    portfolio.router,
    prefix="/api/v1",
)

app.include_router(
    documents.router,
    prefix="/api/v1",
)

app.include_router(
    health.router,
    prefix="/api/v1",
)


# ============================================================
# DATABASE HEALTH HELPERS
# ============================================================

def get_database_table_counts():
    """
    Return row counts for all user tables in SQLite.
    """

    if not DB_PATH.exists():
        return {
            "database_exists": False,
            "database_path": str(DB_PATH),
            "tables": {},
        }

    counts = {}

    with sqlite3.connect(DB_PATH) as conn:

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        for (table_name,) in tables:

            try:
                count = conn.execute(
                    f'''
                    SELECT COUNT(*)
                    FROM "{table_name}"
                    '''
                ).fetchone()[0]

                counts[table_name] = count

            except sqlite3.Error:
                counts[table_name] = None

    return {
        "database_exists": True,
        "database_path": str(DB_PATH),
        "tables": counts,
    }


# ============================================================
# HEALTH DETAILS
# ============================================================

@app.get("/api/v1/system/health")
def system_health():
    """
    Detailed system health information.

    Includes:
    - API status
    - database status
    - table row counts
    - uptime
    - version
    """

    uptime_seconds = (
        time.time() - START_TIME
    )

    database_info = (
        get_database_table_counts()
    )

    return {
        "status": "healthy",
        "version": API_VERSION,
        "uptime_seconds": round(
            uptime_seconds,
            2,
        ),
        "checked_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "database": database_info,
    }