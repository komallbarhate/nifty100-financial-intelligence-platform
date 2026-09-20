from pathlib import Path
import sqlite3

from fastapi import APIRouter, Query

router = APIRouter(prefix="/screener", tags=["Screener"])

BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "data" / "nifty100.db"


def get_connection():
    if not DB_PATH.exists():
        raise RuntimeError(f"Database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@router.get("/")
def screen_companies(
    sector: str | None = Query(default=None),
    min_roe: float | None = Query(default=None),
    max_debt_to_equity: float | None = Query(default=None),
    min_revenue_cagr_5yr: float | None = Query(default=None),
    min_opm: float | None = Query(default=None),
    min_fcf: float | None = Query(default=None),
):
    """
    Screen companies using latest available financial-ratio data.

    Optional filters:
    - sector
    - min_roe
    - max_debt_to_equity
    - min_revenue_cagr_5yr
    - min_opm
    - min_fcf
    """

    connection = get_connection()

    try:
        query = """
            SELECT
                c.id AS company_id,
                c.company_name,
                s.sector,
                s.industry,
                fr.year,
                fr.return_on_equity_pct,
                fr.debt_to_equity,
                fr.revenue_cagr_5yr,
                fr.operating_profit_margin_pct,
                fr.free_cash_flow_cr,
                fr.composite_quality_score
            FROM companies c
            LEFT JOIN sectors s
                ON c.id = s.company_id
            JOIN financial_ratios fr
                ON c.id = fr.company_id
            WHERE fr.year = (
                SELECT MAX(fr2.year)
                FROM financial_ratios fr2
                WHERE fr2.company_id = c.id
            )
        """

        parameters = []

        if sector:
            query += " AND s.sector = ?"
            parameters.append(sector)

        if min_roe is not None:
            query += " AND fr.return_on_equity_pct >= ?"
            parameters.append(min_roe)

        if max_debt_to_equity is not None:
            query += " AND fr.debt_to_equity <= ?"
            parameters.append(max_debt_to_equity)

        if min_revenue_cagr_5yr is not None:
            query += " AND fr.revenue_cagr_5yr >= ?"
            parameters.append(min_revenue_cagr_5yr)

        if min_opm is not None:
            query += " AND fr.operating_profit_margin_pct >= ?"
            parameters.append(min_opm)

        if min_fcf is not None:
            query += " AND fr.free_cash_flow_cr >= ?"
            parameters.append(min_fcf)

        query += " ORDER BY fr.composite_quality_score DESC"

        rows = connection.execute(query, parameters).fetchall()

        results = [dict(row) for row in rows]

        return {
            "count": len(results),
            "filters": {
                "sector": sector,
                "min_roe": min_roe,
                "max_debt_to_equity": max_debt_to_equity,
                "min_revenue_cagr_5yr": min_revenue_cagr_5yr,
                "min_opm": min_opm,
                "min_fcf": min_fcf,
            },
            "results": results,
        }

    finally:
        connection.close()