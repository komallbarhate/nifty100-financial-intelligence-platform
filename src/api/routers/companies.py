"""
Company API endpoints.

Day 39 — Company API
"""

import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


BASE_DIR = Path(__file__).resolve().parents[3]

DB_PATH = BASE_DIR / "data" / "nifty100.db"


# ============================================================
# DATABASE HELPER
# ============================================================


def get_connection():
    """Create a SQLite connection with dictionary-style rows."""

    if not DB_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="Database not found.",
        )

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# GET ALL COMPANIES
# ============================================================


@router.get("/")
def get_companies():
    """
    Return all NIFTY 100 companies.

    Includes:
    - company ID
    - company name
    - sector
    - industry
    """

    with get_connection() as conn:

        rows = conn.execute("""
            SELECT
                c.id AS company_id,
                c.company_name,
                s.sector,
                s.industry
            FROM companies c
            LEFT JOIN sectors s
                ON c.id = s.company_id
            ORDER BY c.company_name
            """).fetchall()

    return {
        "count": len(rows),
        "companies": [dict(row) for row in rows],
    }


# ============================================================
# GET ONE COMPANY
# ============================================================


@router.get("/{company_id}")
def get_company(
    company_id: str,
):
    """
    Return complete company master information.
    """

    with get_connection() as conn:

        row = conn.execute(
            """
            SELECT
                c.id AS company_id,
                c.company_name,
                c.company_logo,
                c.chart_link,
                c.about_company,
                c.website,
                c.nse_profile,
                c.bse_profile,
                c.face_value,
                c.book_value,
                c.roce_percentage,
                c.roe_percentage,
                s.sector,
                s.industry
            FROM companies c
            LEFT JOIN sectors s
                ON c.id = s.company_id
            WHERE c.id = ?
            """,
            (company_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Company '{company_id}' not found.",
        )

    return dict(row)


# ============================================================
# COMPANY FINANCIALS
# ============================================================


@router.get("/{company_id}/financials")
def get_company_financials(
    company_id: str,
):
    """
    Return historical profit and loss information.
    """

    with get_connection() as conn:

        company = conn.execute(
            """
            SELECT
                id,
                company_name
            FROM companies
            WHERE id = ?
            """,
            (company_id,),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found.",
            )

        rows = conn.execute(
            """
            SELECT
                id,
                company_id,
                year,
                sales,
                expenses,
                operating_profit,
                opm_percentage,
                other_income,
                interest,
                depreciation,
                profit_before_tax,
                tax_percentage,
                net_profit,
                eps,
                dividend_payout
            FROM profitandloss
            WHERE company_id = ?
            ORDER BY year
            """,
            (company_id,),
        ).fetchall()

    return {
        "company_id": company["id"],
        "company_name": company["company_name"],
        "count": len(rows),
        "financials": [dict(row) for row in rows],
    }


# ============================================================
# COMPANY RATIOS
# ============================================================


@router.get("/{company_id}/ratios")
def get_company_ratios(
    company_id: str,
):
    """
    Return historical financial ratios and KPI calculations.
    """

    with get_connection() as conn:

        company = conn.execute(
            """
            SELECT
                id,
                company_name
            FROM companies
            WHERE id = ?
            """,
            (company_id,),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found.",
            )

        rows = conn.execute(
            """
            SELECT *
            FROM financial_ratios
            WHERE company_id = ?
            ORDER BY year
            """,
            (company_id,),
        ).fetchall()

    return {
        "company_id": company["id"],
        "company_name": company["company_name"],
        "count": len(rows),
        "ratios": [dict(row) for row in rows],
    }


# ============================================================
# COMPANY VALUATION
# ============================================================


@router.get("/{company_id}/valuation")
def get_company_valuation(
    company_id: str,
):
    """
    Return historical market-cap and valuation metrics.
    """

    with get_connection() as conn:

        company = conn.execute(
            """
            SELECT
                id,
                company_name
            FROM companies
            WHERE id = ?
            """,
            (company_id,),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found.",
            )

        rows = conn.execute(
            """
            SELECT
                id,
                company_id,
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
        "company_id": company["id"],
        "company_name": company["company_name"],
        "count": len(rows),
        "valuation": [dict(row) for row in rows],
    }


# ============================================================
# COMPANY PEERS
# ============================================================


@router.get("/{company_id}/peers")
def get_company_peers(
    company_id: str,
):
    """
    Return companies belonging to the same peer group.

    A peer group is defined by the peer_groups table.
    The requested company itself is excluded from the result.

    If the company has no peer-group assignment, an empty
    peer list is returned rather than inventing a group.
    """

    with get_connection() as conn:

        company = conn.execute(
            """
            SELECT
                id,
                company_name
            FROM companies
            WHERE id = ?
            """,
            (company_id,),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found.",
            )

        peer_group = conn.execute(
            """
            SELECT peer_group
            FROM peer_groups
            WHERE company_id = ?
            """,
            (company_id,),
        ).fetchone()

        if peer_group is None:
            return {
                "company_id": company["id"],
                "company_name": company["company_name"],
                "peer_group": None,
                "count": 0,
                "peers": [],
            }

        group_name = peer_group["peer_group"]

        rows = conn.execute(
            """
            SELECT
                c.id AS company_id,
                c.company_name,
                s.sector,
                s.industry
            FROM peer_groups pg
            INNER JOIN companies c
                ON pg.company_id = c.id
            LEFT JOIN sectors s
                ON c.id = s.company_id
            WHERE pg.peer_group = ?
              AND pg.company_id != ?
            ORDER BY c.company_name
            """,
            (
                group_name,
                company_id,
            ),
        ).fetchall()

    return {
        "company_id": company["id"],
        "company_name": company["company_name"],
        "peer_group": group_name,
        "count": len(rows),
        "peers": [dict(row) for row in rows],
    }


# ============================================================
# COMPANY DOCUMENTS
# ============================================================


@router.get("/{company_id}/documents")
def get_company_documents(
    company_id: str,
):
    """
    Return documents associated with a company.
    """

    with get_connection() as conn:

        company = conn.execute(
            """
            SELECT
                id,
                company_name
            FROM companies
            WHERE id = ?
            """,
            (company_id,),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found.",
            )

        rows = conn.execute(
            """
            SELECT *
            FROM documents
            WHERE company_id = ?
            ORDER BY id
            """,
            (company_id,),
        ).fetchall()

    return {
        "company_id": company["id"],
        "company_name": company["company_name"],
        "count": len(rows),
        "documents": [dict(row) for row in rows],
    }
