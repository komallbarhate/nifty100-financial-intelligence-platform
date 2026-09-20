import os
import sqlite3

DB_PATH = "data/nifty100.db"

conn = sqlite3.connect(DB_PATH)

print("=" * 50)
print("NIFTY 100 FINAL DATABASE VERIFICATION")
print("=" * 50)

print("DATABASE:", os.path.exists(DB_PATH))

tables = conn.execute(
    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
).fetchone()[0]

companies = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]

fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()

integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]

tables_expected = [
    "analysis",
    "balancesheet",
    "cashflow",
    "companies",
    "documents",
    "financial_ratios",
    "market_cap",
    "peer_groups",
    "profitandloss",
    "prosandcons",
    "sectors",
    "stock_prices",
]

print("TABLES:", tables)
print("COMPANIES:", companies)
print("FOREIGN KEY ERRORS:", fk_errors)
print("INTEGRITY:", integrity)

print("\nTABLE CHECK")
print("-" * 50)

actual_tables = [
    row[0]
    for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
]

for table in tables_expected:
    if table in actual_tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count}")
    else:
        print(f"{table}: MISSING")

print("\nFINAL STATUS")
print("-" * 50)

if (
    os.path.exists(DB_PATH)
    and tables == 12
    and companies == 92
    and len(fk_errors) == 0
    and integrity == "ok"
    and all(table in actual_tables for table in tables_expected)
):
    print("DATABASE VERIFICATION: PASSED")
else:
    print("DATABASE VERIFICATION: FAILED")

print("=" * 50)

conn.close()
