"""
Sprint 6 - Day 43
Database performance indexes.

Creates only the indexes required for the API's common query patterns.
All indexes use IF NOT EXISTS so this script is safe to run repeatedly.
"""

from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "nifty100.db"


INDEXES = {
    "idx_financial_ratios_company_year": """
        CREATE INDEX IF NOT EXISTS idx_financial_ratios_company_year
        ON financial_ratios(company_id, year)
    """,
    "idx_financial_ratios_year": """
        CREATE INDEX IF NOT EXISTS idx_financial_ratios_year
        ON financial_ratios(year)
    """,
    "idx_market_cap_company_year": """
        CREATE INDEX IF NOT EXISTS idx_market_cap_company_year
        ON market_cap(company_id, year)
    """,
    "idx_documents_company_year": """
        CREATE INDEX IF NOT EXISTS idx_documents_company_year
        ON documents(company_id, year)
    """,
    "idx_sectors_company": """
        CREATE INDEX IF NOT EXISTS idx_sectors_company
        ON sectors(company_id)
    """,
    "idx_peer_groups_company": """
        CREATE INDEX IF NOT EXISTS idx_peer_groups_company
        ON peer_groups(company_id)
    """,
    "idx_peer_percentiles_company_group_year": """
        CREATE INDEX IF NOT EXISTS idx_peer_percentiles_company_group_year
        ON peer_percentiles(company_id, peer_group, year)
    """,
}


def get_existing_indexes(conn):
    """Return all user-created SQLite indexes."""

    rows = conn.execute(
        """
        SELECT name, tbl_name
        FROM sqlite_master
        WHERE type = 'index'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY tbl_name, name
        """
    ).fetchall()

    return rows


def main():
    """Create required performance indexes and print the final index list."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    print(f"Database: {DB_PATH}")
    print()

    with sqlite3.connect(DB_PATH) as conn:

        before = get_existing_indexes(conn)

        print(f"Indexes before: {len(before)}")

        for name, table in before:
            print(f"  {name} -> {table}")

        print()
        print("Creating required API indexes...")

        for index_name, sql in INDEXES.items():
            conn.execute(sql)
            print(f"  OK: {index_name}")

        conn.commit()

        after = get_existing_indexes(conn)

        print()
        print(f"Indexes after: {len(after)}")

        for name, table in after:
            print(f"  {name} -> {table}")

        print()
        print(
            f"Added or confirmed {len(INDEXES)} "
            "performance indexes."
        )


if __name__ == "__main__":
    main()