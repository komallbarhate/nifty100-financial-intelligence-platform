import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = "data/nifty100.db"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH)

# Use latest available year for each company.
df = pd.read_sql_query("""
WITH latest AS (
    SELECT
        company_id,
        MAX(year) AS year
    FROM financial_ratios
    WHERE year IS NOT NULL
    GROUP BY company_id
)
SELECT
    r.company_id,
    r.year,

    r.net_profit_margin_pct,
    r.operating_profit_margin_pct,
    r.return_on_equity_pct,
    r.return_on_capital_employed_pct,
    r.return_on_assets_pct,
    r.debt_to_equity,
    r.interest_coverage,
    r.asset_turnover,
    r.free_cash_flow_cr,
    r.capex_intensity_pct,
    r.earnings_per_share,
    r.book_value_per_share,
    r.dividend_payout_ratio_pct,
    r.total_debt_cr,
    r.cash_from_operations_cr,
    r.cfo_pat_ratio,
    r.revenue_cagr_5yr,
    r.pat_cagr_5yr,
    r.eps_cagr_5yr,
    r.composite_quality_score,

    s.sector,
    s.industry,

    c.company_name

FROM financial_ratios r

JOIN latest l
    ON r.company_id = l.company_id
   AND r.year = l.year

LEFT JOIN sectors s
    ON r.company_id = s.company_id

LEFT JOIN companies c
    ON r.company_id = c.id

ORDER BY r.composite_quality_score DESC
""", conn)

print("=" * 80)
print("DAY 14 - FINANCIAL SCREENER")
print("=" * 80)

print("\nLatest-year company records:", len(df))
print("Companies:", df["company_id"].nunique())

# -------------------------------------------------------------------
# SCREEN 1 — PROFITABILITY
# -------------------------------------------------------------------

profitability = df[
    (df["return_on_equity_pct"] > 15)
    &
    (df["net_profit_margin_pct"] > 10)
].copy()

profitability = profitability.sort_values(
    "composite_quality_score",
    ascending=False
)

# -------------------------------------------------------------------
# SCREEN 2 — GROWTH
# -------------------------------------------------------------------

growth = df[
    (df["revenue_cagr_5yr"].notna())
    &
    (df["revenue_cagr_5yr"] > 10)
    &
    (df["pat_cagr_5yr"].notna())
    &
    (df["pat_cagr_5yr"] > 10)
].copy()

growth = growth.sort_values(
    "revenue_cagr_5yr",
    ascending=False
)

# -------------------------------------------------------------------
# SCREEN 3 — BALANCE SHEET
# -------------------------------------------------------------------

balance_sheet = df[
    (
        df["debt_to_equity"].isna()
        |
        (df["debt_to_equity"] < 2)
    )
    &
    (
        df["interest_coverage"].isna()
        |
        (df["interest_coverage"] > 3)
    )
].copy()

balance_sheet = balance_sheet.sort_values(
    "composite_quality_score",
    ascending=False
)

# -------------------------------------------------------------------
# SCREEN 4 — CASH FLOW
# -------------------------------------------------------------------

cashflow = df[
    (df["free_cash_flow_cr"] > 0)
    &
    (df["cash_from_operations_cr"] > 0)
].copy()

cashflow = cashflow.sort_values(
    "composite_quality_score",
    ascending=False
)

# -------------------------------------------------------------------
# SAVE SCREEN RESULTS
# -------------------------------------------------------------------

profitability.to_csv(
    OUTPUT_DIR / "screener_profitability.csv",
    index=False
)

growth.to_csv(
    OUTPUT_DIR / "screener_growth.csv",
    index=False
)

balance_sheet.to_csv(
    OUTPUT_DIR / "screener_balance_sheet.csv",
    index=False
)

cashflow.to_csv(
    OUTPUT_DIR / "screener_cashflow.csv",
    index=False
)

# -------------------------------------------------------------------
# 5-COMPANY DEMO
# -------------------------------------------------------------------

demo = df.sort_values(
    "composite_quality_score",
    ascending=False
).head(5).copy()

demo_columns = [
    "company_id",
    "company_name",
    "year",
    "sector",
    "net_profit_margin_pct",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "debt_to_equity",
    "interest_coverage",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "eps_cagr_5yr",
    "composite_quality_score",
]

demo = demo[demo_columns]

demo.to_csv(
    OUTPUT_DIR / "day14_five_company_demo.csv",
    index=False
)

# -------------------------------------------------------------------
# PRINT RESULTS
# -------------------------------------------------------------------

print("\n1. PROFITABILITY SCREEN")
print("-" * 80)
print(
    profitability[
        [
            "company_id",
            "company_name",
            "year",
            "return_on_equity_pct",
            "net_profit_margin_pct",
            "composite_quality_score",
        ]
    ].head(10).to_string(index=False)
)

print("\n2. GROWTH SCREEN")
print("-" * 80)
print(
    growth[
        [
            "company_id",
            "company_name",
            "year",
            "revenue_cagr_5yr",
            "pat_cagr_5yr",
            "eps_cagr_5yr",
        ]
    ].head(10).to_string(index=False)
)

print("\n3. BALANCE-SHEET SCREEN")
print("-" * 80)
print(
    balance_sheet[
        [
            "company_id",
            "company_name",
            "year",
            "debt_to_equity",
            "interest_coverage",
            "composite_quality_score",
        ]
    ].head(10).to_string(index=False)
)

print("\n4. CASH-FLOW SCREEN")
print("-" * 80)
print(
    cashflow[
        [
            "company_id",
            "company_name",
            "year",
            "free_cash_flow_cr",
            "cash_from_operations_cr",
            "composite_quality_score",
        ]
    ].head(10).to_string(index=False)
)

print("\n5. FIVE-COMPANY DEMO")
print("-" * 80)
print(demo.to_string(index=False))

print("\n6. OUTPUT FILES")
print("-" * 80)

for filename in [
    "screener_profitability.csv",
    "screener_growth.csv",
    "screener_balance_sheet.csv",
    "screener_cashflow.csv",
    "day14_five_company_demo.csv",
]:
    path = OUTPUT_DIR / filename
    print(
        f"{'PASS' if path.exists() else 'FAIL'} - {path}"
    )

conn.close()

print("\n" + "=" * 80)
print("DAY 14 SCREENER: COMPLETE")
print("=" * 80)
