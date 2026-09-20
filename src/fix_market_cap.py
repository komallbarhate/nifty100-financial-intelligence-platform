import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
SOURCE_PATH = (
    PROJECT_ROOT / "data" / "supporting" / "1788501620397-69ae3e7f-market_cap.xlsx"
)

df = pd.read_excel(SOURCE_PATH)

df["company_id"] = df["company_id"].astype(str).str.strip()
df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

numeric_columns = [
    "market_cap_crore",
    "enterprise_value_crore",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "dividend_yield_pct",
]

for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")

df = df.dropna(subset=["company_id", "year"]).copy()
df["year"] = df["year"].astype(int)

conn = sqlite3.connect(DB_PATH)

conn.execute("DROP TABLE IF EXISTS market_cap")

conn.execute("""
CREATE TABLE market_cap (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    market_cap_crore REAL,
    enterprise_value_crore REAL,
    pe_ratio REAL,
    pb_ratio REAL,
    ev_ebitda REAL,
    dividend_yield_pct REAL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
)
""")

rows = []
for row in df.itertuples(index=False):
    rows.append(
        (
            row.id,
            row.company_id,
            row.year,
            row.market_cap_crore,
            row.enterprise_value_crore,
            row.pe_ratio,
            row.pb_ratio,
            row.ev_ebitda,
            row.dividend_yield_pct,
        )
    )

conn.executemany(
    """
INSERT INTO market_cap (
    id,
    company_id,
    year,
    market_cap_crore,
    enterprise_value_crore,
    pe_ratio,
    pb_ratio,
    ev_ebitda,
    dividend_yield_pct
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""",
    rows,
)

conn.commit()

count = conn.execute("SELECT COUNT(*) FROM market_cap").fetchone()[0]
companies = conn.execute(
    "SELECT COUNT(DISTINCT company_id) FROM market_cap"
).fetchone()[0]

print("=" * 60)
print("MARKET CAP TABLE REBUILT")
print("=" * 60)
print(f"Rows: {count}")
print(f"Companies: {companies}")
print()
print("Schema:")
for column in conn.execute("PRAGMA table_info(market_cap)").fetchall():
    print(column)
print()
print("Sample:")
for row in conn.execute("""
    SELECT company_id, year, market_cap_crore, pe_ratio,
           pb_ratio, dividend_yield_pct
    FROM market_cap
    ORDER BY company_id, year
    LIMIT 5
""").fetchall():
    print(row)

conn.close()
