import sqlite3
import os

DB_PATH = "data/nifty100.db"

print("=" * 70)
print("FIXING MARKET_CAP FOREIGN KEY")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = OFF")

old_count = conn.execute(
    "SELECT COUNT(*) FROM market_cap"
).fetchone()[0]

print(f"Existing market_cap rows: {old_count}")

conn.execute("DROP TABLE market_cap")

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
    FOREIGN KEY (company_id) REFERENCES companies(id)
)
""")

source_path = os.path.join(
    "data",
    "supporting",
    "1788501620397-69ae3e7f-market_cap.xlsx"
)

import pandas as pd

df = pd.read_excel(source_path, header=0)

df["company_id"] = df["company_id"].astype(str).str.strip()
df.loc[df["company_id"] == "BAJAJ-AUTO", "company_id"] = "BAJAJAUTO"

columns = [
    "id",
    "company_id",
    "year",
    "market_cap_crore",
    "enterprise_value_crore",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "dividend_yield_pct",
]

df = df[columns]

records = [
    tuple(row)
    for row in df.itertuples(index=False, name=None)
]

conn.executemany("""
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
""", records)

conn.commit()

new_count = conn.execute(
    "SELECT COUNT(*) FROM market_cap"
).fetchone()[0]

print(f"New market_cap rows: {new_count}")

print()
print("NEW FOREIGN KEY:")
for row in conn.execute(
    "PRAGMA foreign_key_list(market_cap)"
).fetchall():
    print(row)

print()
print("FOREIGN KEY CHECK:")
conn.execute("PRAGMA foreign_keys = ON")

errors = conn.execute(
    "PRAGMA foreign_key_check"
).fetchall()

print(f"Foreign-key errors: {len(errors)}")

if errors:
    for error in errors[:20]:
        print(error)
    raise SystemExit("Foreign-key validation failed.")

print()
print("INTEGRITY CHECK:")
integrity = conn.execute(
    "PRAGMA integrity_check"
).fetchone()[0]

print(integrity)

if integrity != "ok":
    raise SystemExit("SQLite integrity check failed.")

conn.close()

print()
print("=" * 70)
print("MARKET_CAP FOREIGN KEY FIX COMPLETE")
print("=" * 70)
