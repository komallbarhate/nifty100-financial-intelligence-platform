import sqlite3
import pandas as pd

DB_PATH = "data/nifty100.db"

conn = sqlite3.connect(DB_PATH)

print("=" * 80)
print("DAY 14 - KPI COVERAGE VALIDATION")
print("=" * 80)

df = pd.read_sql_query(
    "SELECT * FROM financial_ratios",
    conn
)

print("\n1. RATIO TABLE")
print("-" * 80)
print("Rows:", len(df))
print("Companies:", df["company_id"].nunique())
print("Years:", df["year"].min(), "to", df["year"].max())

kpis = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "return_on_assets_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow_cr",
    "capex_cr",
    "earnings_per_share",
    "book_value_per_share",
    "dividend_payout_ratio_pct",
    "total_debt_cr",
    "cash_from_operations_cr",
    "cfo_pat_ratio",
    "capex_intensity_pct",
    "fcf_conversion_rate_pct",
    "revenue_cagr_3yr",
    "revenue_cagr_5yr",
    "revenue_cagr_10yr",
    "pat_cagr_3yr",
    "pat_cagr_5yr",
    "pat_cagr_10yr",
    "eps_cagr_3yr",
    "eps_cagr_5yr",
    "eps_cagr_10yr",
    "composite_quality_score",
]

print("\n2. KPI POPULATION")
print("-" * 80)

results = []

for kpi in kpis:
    if kpi not in df.columns:
        results.append({
            "kpi": kpi,
            "non_null": 0,
            "population_pct": 0,
            "status": "MISSING COLUMN"
        })
        continue

    non_null = int(df[kpi].notna().sum())
    population_pct = round(non_null / len(df) * 100, 2)

    results.append({
        "kpi": kpi,
        "non_null": non_null,
        "population_pct": population_pct,
        "status": "PASS" if non_null > 0 else "FAIL"
    })

coverage = pd.DataFrame(results)

print(coverage.to_string(index=False))

print("\n3. KEY SPRINT 2 KPIs")
print("-" * 80)

key_kpis = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "eps_cagr_5yr",
    "composite_quality_score",
]

for kpi in key_kpis:
    if kpi in df.columns:
        print(
            f"{kpi:35} "
            f"{df[kpi].notna().sum():4}/{len(df)}"
        )

print("\n4. FINANCIAL RATIOS TABLE COLUMNS")
print("-" * 80)

print("Total columns:", len(df.columns))

for col in df.columns:
    print(col)

print("\n5. DATABASE INTEGRITY")
print("-" * 80)

fk = conn.execute("PRAGMA foreign_key_check").fetchall()
integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]

print("Foreign-key errors:", len(fk))
print("Integrity check:", integrity)

print("\n" + "=" * 80)

if (
    len(df) >= 1000
    and df["company_id"].nunique() == 92
    and len(fk) == 0
    and integrity == "ok"
):
    print("DAY 14 KPI COVERAGE: PASS")
else:
    print("DAY 14 KPI COVERAGE: NEEDS REVIEW")

print("=" * 80)

conn.close()
