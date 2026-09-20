import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/valuation", tags=["Valuation"])

BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "data" / "nifty100.db"


def get_connection():
    """Return connection."""
    if not DB_PATH.exists():
        raise RuntimeError(f"Database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@router.get("/market-cap")
def market_cap(
    company_id: str | None = Query(default=None),
    year: int | None = Query(default=None),
):
    """Process market cap."""
    connection = get_connection()

    try:
        query = """
            SELECT
                mc.company_id,
                c.company_name,
                mc.year,
                mc.market_cap_crore,
                mc.enterprise_value_crore,
                mc.pe_ratio,
                mc.pb_ratio,
                mc.ev_ebitda,
                mc.dividend_yield_pct
            FROM market_cap mc
            JOIN companies c
                ON c.id = mc.company_id
            WHERE 1 = 1
        """

        params = []

        if company_id:
            query += " AND mc.company_id = ?"
            params.append(company_id)

        if year is not None:
            query += " AND mc.year = ?"
            params.append(year)

        query += " ORDER BY mc.market_cap_crore DESC"

        rows = connection.execute(query, params).fetchall()

        return {
            "count": len(rows),
            "results": [dict(row) for row in rows],
        }

    finally:
        connection.close()


@router.get("/market-cap/{company_id}")
def company_market_cap(company_id: str):
    """Process company market cap."""
    connection = get_connection()

    try:
        company = connection.execute(
            "SELECT id, company_name FROM companies WHERE id = ?",
            (company_id,),
        ).fetchone()

        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Company not found: {company_id}",
            )

        rows = connection.execute(
            """
            SELECT
                year,
                market_cap_crore,
                enterprise_value_crore,
                pe_ratio,
                pb_ratio,
                ev_ebitda,
                dividend_yield_pct
            FROM market_cap
            WHERE company_id = ?
            ORDER BY year
            """,
            (company_id,),
        ).fetchall()

        return {
            "company_id": company_id,
            "company_name": company["company_name"],
            "count": len(rows),
            "history": [dict(row) for row in rows],
        }

    finally:
        connection.close()
