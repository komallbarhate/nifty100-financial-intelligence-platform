import sqlite3

import pandas as pd

DB_PATH = "data/nifty100.db"

conn = sqlite3.connect(DB_PATH)

print("=" * 70)
print("DAY 12 - DIAGNOSTIC CHECK")
print("=" * 70)

print("\nBALANCE SHEET COLUMNS")
print("-" * 70)

bs = pd.read_sql_query("SELECT * FROM balancesheet LIMIT 5", conn)

print(bs.columns.tolist())
print(bs.head().to_string())

print("\nP&L COLUMNS")
print("-" * 70)

pnl = pd.read_sql_query("SELECT * FROM profitandloss LIMIT 5", conn)

print(pnl.columns.tolist())
print(pnl.head().to_string())

print("\nNULL YEAR COUNTS")
print("-" * 70)

for table in ["profitandloss", "balancesheet", "cashflow"]:
    result = pd.read_sql_query(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            SUM(CASE WHEN year IS NULL THEN 1 ELSE 0 END) AS null_years
        FROM {table}
        """,
        conn,
    )

    print(table)
    print(result.to_string(index=False))

print("\nBALANCE SHEET EQUITY / DEBT AVAILABILITY")
print("-" * 70)

result = pd.read_sql_query(
    """
    SELECT
        COUNT(*) AS total,
        SUM(
            CASE
                WHEN share_capital IS NOT NULL
                 AND reserves IS NOT NULL
                THEN 1 ELSE 0
            END
        ) AS equity_available,
        SUM(
            CASE
                WHEN borrowings IS NOT NULL
                THEN 1 ELSE 0
            END
        ) AS borrowings_available
    FROM balancesheet
    """,
    conn,
)

print(result.to_string(index=False))

print("\nSAMPLE BALANCE SHEET VALUES")
print("-" * 70)

result = pd.read_sql_query(
    """
    SELECT
        company_id,
        year,
        share_capital,
        reserves,
        borrowings
    FROM balancesheet
    WHERE year IS NOT NULL
    LIMIT 20
    """,
    conn,
)

print(result.to_string(index=False))

conn.close()

print("\nDIAGNOSTIC COMPLETE")
print("=" * 70)
