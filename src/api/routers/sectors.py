import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/sectors", tags=["Sectors"])

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
def list_sectors():
    """
    Return all sectors with company counts.
    """

    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT
                s.sector,
                COUNT(DISTINCT s.company_id) AS company_count
            FROM sectors s
            GROUP BY s.sector
            ORDER BY s.sector
            """).fetchall()

        results = [dict(row) for row in rows]

        return {
            "count": len(results),
            "sectors": results,
        }

    finally:
        connection.close()


@router.get("/{sector_name}")
def get_sector(sector_name: str):
    """
    Return companies belonging to a sector.
    """

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                c.id AS company_id,
                c.company_name,
                s.sector,
                s.industry
            FROM sectors s
            JOIN companies c
                ON c.id = s.company_id
            WHERE LOWER(s.sector) = LOWER(?)
            ORDER BY c.company_name
            """,
            (sector_name,),
        ).fetchall()

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"Sector not found: {sector_name}",
            )

        return {
            "sector": rows[0]["sector"],
            "count": len(rows),
            "companies": [dict(row) for row in rows],
        }

    finally:
        connection.close()


@router.get("/{sector_name}/summary")
def sector_summary(sector_name: str):
    """
    Return latest financial-ratio summary for a sector.
    """

    connection = get_connection()

    try:
        sector_exists = connection.execute(
            """
            SELECT 1
            FROM sectors
            WHERE LOWER(sector) = LOWER(?)
            LIMIT 1
            """,
            (sector_name,),
        ).fetchone()

        if not sector_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Sector not found: {sector_name}",
            )

        row = connection.execute(
            """
            SELECT
                s.sector,
                COUNT(DISTINCT fr.company_id) AS company_count,
                AVG(fr.return_on_equity_pct) AS average_roe,
                AVG(fr.debt_to_equity) AS average_debt_to_equity,
                AVG(fr.revenue_cagr_5yr) AS average_revenue_cagr_5yr,
                AVG(fr.operating_profit_margin_pct) AS average_opm,
                AVG(fr.free_cash_flow_cr) AS average_free_cash_flow_cr,
                AVG(fr.composite_quality_score) AS average_quality_score
            FROM sectors s
            JOIN financial_ratios fr
                ON s.company_id = fr.company_id
            WHERE LOWER(s.sector) = LOWER(?)
              AND fr.year = (
                  SELECT MAX(fr2.year)
                  FROM financial_ratios fr2
                  WHERE fr2.company_id = fr.company_id
              )
            GROUP BY s.sector
            """,
            (sector_name,),
        ).fetchone()

        return {"sector": dict(row)}

    finally:
        connection.close()
