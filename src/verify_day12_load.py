import sqlite3

import pandas as pd

conn = sqlite3.connect("data/nifty100.db")

print("=" * 70)
print("POST-LOAD VERIFICATION")
print("=" * 70)

print("\nEQUITY / DEBT AVAILABILITY")
print("-" * 70)

result = pd.read_sql_query(
    """
    SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN share_capital IS NOT NULL THEN 1 ELSE 0 END) AS share_capital_available,
        SUM(CASE WHEN reserves IS NOT NULL THEN 1 ELSE 0 END) AS reserves_available,
        SUM(CASE WHEN borrowings IS NOT NULL THEN 1 ELSE 0 END) AS borrowings_available
    FROM balancesheet
    """,
    conn,
)

print(result.to_string(index=False))

print("\nSAMPLE BALANCE SHEET")
print("-" * 70)

result = pd.read_sql_query(
    """
    SELECT
        company_id,
        year,
        share_capital,
        reserves,
        borrowings,
        total_assets
    FROM balancesheet
    WHERE company_id IN ('ABB', 'ADANIENSOL', 'TCS')
    ORDER BY company_id, year
    LIMIT 20
    """,
    conn,
)

print(result.to_string(index=False))

print("\nP&L YEAR COVERAGE")
print("-" * 70)

result = pd.read_sql_query(
    """
    SELECT
        COUNT(*) AS total_rows,
        SUM(CASE WHEN year IS NULL THEN 1 ELSE 0 END) AS null_years,
        COUNT(DISTINCT company_id) AS companies,
        MIN(year) AS min_year,
        MAX(year) AS max_year
    FROM profitandloss
    """,
    conn,
)

print(result.to_string(index=False))

conn.close()

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
