"""
Health API router.
"""

from pathlib import Path
import sqlite3
import time

from fastapi import APIRouter


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


BASE_DIR = Path(__file__).resolve().parents[3]

DB_PATH = (
    BASE_DIR
    / "data"
    / "nifty100.db"
)

START_TIME = time.time()


@router.get("/")
def health_check():
    """
    Basic API and database health check.
    """

    database_status = "healthy"

    if not DB_PATH.exists():
        database_status = "missing"

    else:
        try:
            with sqlite3.connect(
                DB_PATH
            ) as conn:
                conn.execute(
                    "SELECT 1"
                )
        except sqlite3.Error:
            database_status = "error"

    return {
        "status": (
            "healthy"
            if database_status == "healthy"
            else "degraded"
        ),
        "database": database_status,
        "uptime_seconds": round(
            time.time() - START_TIME,
            2,
        ),
        "version": "1.0.0",
    }