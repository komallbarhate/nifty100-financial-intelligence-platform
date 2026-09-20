import sqlite3
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/documents", tags=["Documents"])

BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "data" / "nifty100.db"


def get_connection():
    """Return connection."""
    if not DB_PATH.exists():
        raise RuntimeError(f"Database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@router.get("/")
def search_documents(
    company_id: str | None = Query(default=None),
    year: int | None = Query(default=None),
):
    """Process search documents."""
    connection = get_connection()

    try:
        query = """
            SELECT
                d.id,
                d.company_id,
                c.company_name,
                d.year,
                d.document
            FROM documents d
            LEFT JOIN companies c
                ON c.id = d.company_id
            WHERE 1 = 1
        """

        params = []

        if company_id:
            query += " AND d.company_id = ?"
            params.append(company_id)

        if year is not None:
            query += " AND d.year = ?"
            params.append(year)

        query += " ORDER BY d.company_id, d.year DESC"

        rows = connection.execute(query, params).fetchall()

        return {
            "count": len(rows),
            "documents": [dict(row) for row in rows],
        }

    finally:
        connection.close()
