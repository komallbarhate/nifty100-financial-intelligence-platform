import sqlite3

import pandas as pd

conn = sqlite3.connect("data/nifty100.db")

print("=" * 70)
print("DAY 12 COVERAGE DIAGNOSTIC")
print("=" * 70)

print("\n1. P&L TOTAL VS UNIQUE COMPANY-YEAR")
print("-" * 70)

result = pd.read_sql_query(
    """
    SELECT
        COUNT(*) AS total_rows,
        COUNT(DISTINCT company_id || '|' || year) AS unique_company_years,
        COUNT(DISTINCT company_id) AS companies
    FROM profitandloss
    WHERE company_id IS NOT NULL
      AND year IS NOT NULL
    """,
    conn,
)

print(result.to_string(index=False))

print("\n2. DUPLICATE COMPANY-YEAR RECORDS")
print("-" * 70)

result = pd.read_sql_query(
    """
    SELECT
        company_id,
        year,
        COUNT(*) AS records
    FROM profitandloss
    WHERE company_id IS NOT NULL
      AND year IS NOT NULL
    GROUP BY company_id, year
    HAVING COUNT(*) > 1
    ORDER BY records DESC, company_id, year
    """,
    conn,
)

print(result.to_string(index=False))

print("\n3. NULL-YEAR P&L RECORD")
print("-" * 70)

result = pd.read_sql_query(
    """
    SELECT *
    FROM profitandloss
    WHERE year IS NULL
    """,
    conn,
)

print(result.to_string(index=False))

print("\n4. RECORDS PER COMPANY")
print("-" * 70)

result = pd.read_sql_query(
    """
    SELECT
        company_id,
        COUNT(*) AS pnl_records,
        MIN(year) AS first_year,
        MAX(year) AS last_year
    FROM profitandloss
    WHERE year IS NOT NULL
    GROUP BY company_id
    ORDER BY pnl_records, company_id
    """,
    conn,
)

print(result.to_string(index=False))

conn.close()

print("\n" + "=" * 70)
print("COVERAGE DIAGNOSTIC COMPLETE")
print("=" * 70)
