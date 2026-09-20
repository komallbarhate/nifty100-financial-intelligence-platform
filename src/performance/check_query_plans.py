"""
Sprint 6 - Day 43
SQLite EXPLAIN QUERY PLAN verification.

Checks that the performance indexes created for the API
are actually being considered by SQLite.
"""

from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "nifty100.db"


QUERIES = {
    "financial_ratios_company_year": """
        SELECT *
        FROM financial_ratios
        WHERE company_id = 'RELIANCE'
        ORDER BY year DESC
    """,
    "financial_ratios_year": """
        SELECT *
        FROM financial_ratios
        WHERE year = 2024
    """,
    "market_cap_company_year": """
        SELECT *
        FROM market_cap
        WHERE company_id = 'RELIANCE'
        ORDER BY year DESC
    """,
    "documents_company_year": """
        SELECT *
        FROM documents
        WHERE company_id = 'RELIANCE'
        ORDER BY year DESC
    """,
    "peer_groups_company": """
        SELECT *
        FROM peer_groups
        WHERE company_id = 'BAJAJAUTO'
    """,
    "peer_percentiles_company_group_year": """
        SELECT *
        FROM peer_percentiles
        WHERE company_id = 'ADANIGREEN'
        AND peer_group = 'Power & Utilities'
        ORDER BY year DESC
    """,
}


def main():
    """Run EXPLAIN QUERY PLAN for representative API queries."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    print(f"Database: {DB_PATH}")
    print()

    with sqlite3.connect(DB_PATH) as conn:

        for name, query in QUERIES.items():

            print("=" * 70)
            print(name)
            print("=" * 70)

            rows = conn.execute(
                "EXPLAIN QUERY PLAN " + query
            ).fetchall()

            for row in rows:
                print(row)

            print()


if __name__ == "__main__":
    main()