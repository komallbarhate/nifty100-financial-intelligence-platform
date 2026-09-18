import sqlite3
import pandas as pd

conn = sqlite3.connect("data/nifty100.db")

print("=" * 70)
print("DAY 13 — SECTOR / FINANCIALS DIAGNOSTIC")
print("=" * 70)

print("\n1. SECTOR TABLE")
print("-" * 70)

df = pd.read_sql_query("""
    SELECT sector, COUNT(*) AS companies
    FROM sectors
    GROUP BY sector
    ORDER BY companies DESC
""", conn)

print(df.to_string(index=False))

print("\n2. COMPANIES WITH SECTOR INFORMATION")
print("-" * 70)

df2 = pd.read_sql_query("""
    SELECT
        c.id,
        c.company_name,
        s.sector,
        s.industry
    FROM companies c
    LEFT JOIN sectors s ON c.id = s.company_id
    ORDER BY c.id
""", conn)

print(df2.to_string(index=False))

print("\n3. FINANCIALS CANDIDATES")
print("-" * 70)

financial_keywords = (
    "BANK",
    "FIN",
    "LIFE",
    "GENERAL",
    "INSURANCE",
    "LICI",
    "HDFC",
    "ICICI",
    "BAJAJ",
    "KOTAK",
    "SBI",
    "PNB",
    "CANBK",
    "AXIS",
    "INDUSIND",
    "BANKBARODA",
    "SHRIRAM"
)

financials = df2[
    df2["id"].str.upper().str.contains("|".join(financial_keywords), regex=True, na=False)
]

print(financials[["id", "company_name", "sector", "industry"]].to_string(index=False))

print("\nFinancial candidates:", len(financials))

conn.close()

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
