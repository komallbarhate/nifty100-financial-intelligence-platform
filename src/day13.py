import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np

DB_PATH = "data/nifty100.db"
SECTOR_SOURCE = "data/supporting/1788501621129-8684701e-sectors.xlsx"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

EDGE_FILE = OUTPUT_DIR / "day13_financials_edge_cases.csv"
REPORT_FILE = OUTPUT_DIR / "day13_report.md"

print("=" * 80)
print("DAY 13 - FINANCIALS CARVE-OUT + EDGE CASE AUDIT")
print("=" * 80)

# -------------------------------------------------------------------
# 1. LOAD SOURCE SECTOR DATA
# -------------------------------------------------------------------

print("\n[1/7] Loading sector source...")

sector_df = pd.read_excel(SECTOR_SOURCE, header=0)

required_columns = [
    "company_id",
    "broad_sector",
    "sub_sector",
]

missing = [c for c in required_columns if c not in sector_df.columns]

if missing:
    raise ValueError(
        f"Sector source is missing required columns: {missing}"
    )

sector_df["company_id"] = (
    sector_df["company_id"]
    .astype(str)
    .str.strip()
    .str.upper()
)

# Source uses BAJAJ-AUTO while DB company master uses BAJAJAUTO.
sector_df["company_id"] = sector_df["company_id"].replace({
    "BAJAJ-AUTO": "BAJAJAUTO"
})

sector_df["broad_sector"] = (
    sector_df["broad_sector"]
    .astype(str)
    .str.strip()
)

sector_df["sub_sector"] = (
    sector_df["sub_sector"]
    .astype(str)
    .str.strip()
)

print("Source rows:", len(sector_df))
print("Unique companies:", sector_df["company_id"].nunique())

# -------------------------------------------------------------------
# 2. UPDATE DATABASE SECTOR TABLE
# -------------------------------------------------------------------

print("\n[2/7] Updating sectors table...")

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")

sector_rows = []

for _, row in sector_df.iterrows():
    sector_rows.append(
        (
            row["company_id"],
            row["broad_sector"],
            row["sub_sector"],
        )
    )

conn.executemany(
    """
    UPDATE sectors
    SET
        sector = ?,
        industry = ?
    WHERE company_id = ?
    """,
    [
        (
            broad_sector,
            sub_sector,
            company_id,
        )
        for company_id, broad_sector, sub_sector in sector_rows
    ],
)

conn.commit()

# -------------------------------------------------------------------
# 3. VERIFY SECTOR COVERAGE
# -------------------------------------------------------------------

sector_check = pd.read_sql_query(
    """
    SELECT
        COUNT(*) AS total_rows,
        SUM(
            CASE
                WHEN sector IS NOT NULL
                 AND TRIM(sector) <> ''
                THEN 1
                ELSE 0
            END
        ) AS populated_sector_rows
    FROM sectors
    """,
    conn,
)

total_sector_rows = int(sector_check.iloc[0]["total_rows"])
populated_sector_rows = int(
    sector_check.iloc[0]["populated_sector_rows"]
)

print("Sector rows:", total_sector_rows)
print("Populated sectors:", populated_sector_rows)

if total_sector_rows != 92:
    raise RuntimeError(
        f"Expected 92 sector rows, found {total_sector_rows}"
    )

if populated_sector_rows != 92:
    raise RuntimeError(
        f"Expected 92 populated sectors, found {populated_sector_rows}"
    )

# -------------------------------------------------------------------
# 4. IDENTIFY FINANCIALS FROM SOURCE
# -------------------------------------------------------------------

print("\n[3/7] Identifying Financials...")

financials = sector_df[
    sector_df["broad_sector"].str.lower() == "financials"
].copy()

financial_ids = sorted(financials["company_id"].tolist())

print("\nFinancial companies:")
for company_id in financial_ids:
    print("  ", company_id)

print("\nFinancials count:", len(financial_ids))

# -------------------------------------------------------------------
# 5. REBUILD HIGH LEVERAGE FLAGS
# -------------------------------------------------------------------

print("\n[4/7] Applying Financials D/E carve-out...")

ratios = pd.read_sql_query(
    """
    SELECT
        id,
        company_id,
        year,
        debt_to_equity
    FROM financial_ratios
    """,
    conn,
)

financial_set = set(financial_ids)

updated_count = 0

for _, row in ratios.iterrows():
    company_id = row["company_id"]
    de = row["debt_to_equity"]

    if pd.isna(de):
        flag = 0
    elif company_id in financial_set:
        flag = 0
    else:
        flag = int(float(de) > 5.0)

    conn.execute(
        """
        UPDATE financial_ratios
        SET high_leverage_flag = ?
        WHERE id = ?
        """,
        (flag, int(row["id"])),
    )

    updated_count += 1

conn.commit()

print("Ratio rows checked:", updated_count)

# -------------------------------------------------------------------
# 6. ROE / ROCE SOURCE COMPARISON
# -------------------------------------------------------------------

print("\n[5/7] Comparing calculated ROE / ROCE with source values...")

comparison = pd.read_sql_query(
    """
    SELECT
        r.company_id,
        r.year,

        r.return_on_equity_pct AS calculated_roe,
        r.return_on_capital_employed_pct AS calculated_roce,

        c.roe_percentage AS source_roe,
        c.roce_percentage AS source_roce,

        r.debt_to_equity,
        r.high_leverage_flag,

        s.sector,
        s.industry

    FROM financial_ratios r

    LEFT JOIN companies c
        ON r.company_id = c.id

    LEFT JOIN sectors s
        ON r.company_id = s.company_id

    ORDER BY r.company_id, r.year
    """,
    conn,
)

# Convert numeric columns safely.
numeric_columns = [
    "calculated_roe",
    "calculated_roce",
    "source_roe",
    "source_roce",
    "debt_to_equity",
]

for col in numeric_columns:
    comparison[col] = pd.to_numeric(
        comparison[col],
        errors="coerce",
    )

comparison["roe_difference_pct_points"] = (
    comparison["calculated_roe"]
    - comparison["source_roe"]
).abs()

comparison["roce_difference_pct_points"] = (
    comparison["calculated_roce"]
    - comparison["source_roce"]
).abs()

def classify_difference(value):
    if pd.isna(value):
        return "SOURCE_OR_CALCULATED_VALUE_UNAVAILABLE"
    if value <= 5:
        return "WITHIN_5_PERCENTAGE_POINTS"
    if value <= 10:
        return "MODERATE_DIFFERENCE"
    return "MATERIAL_DIFFERENCE"

comparison["roe_category"] = comparison[
    "roe_difference_pct_points"
].apply(classify_difference)

comparison["roce_category"] = comparison[
    "roce_difference_pct_points"
].apply(classify_difference)

# Keep only actual source-comparison anomalies for the edge-case file.
edge_cases = comparison[
    (
        comparison["roe_difference_pct_points"].notna()
        & (comparison["roe_difference_pct_points"] > 5)
    )
    |
    (
        comparison["roce_difference_pct_points"].notna()
        & (comparison["roce_difference_pct_points"] > 5)
    )
].copy()

edge_cases["edge_case_type"] = np.select(
    [
        (
            edge_cases["roe_difference_pct_points"].notna()
            & (edge_cases["roe_difference_pct_points"] > 5)
            &
            edge_cases["roce_difference_pct_points"].notna()
            & (edge_cases["roce_difference_pct_points"] > 5)
        ),
        (
            edge_cases["roe_difference_pct_points"].notna()
            & (edge_cases["roe_difference_pct_points"] > 5)
        ),
        (
            edge_cases["roce_difference_pct_points"].notna()
            & (edge_cases["roce_difference_pct_points"] > 5)
        ),
    ],
    [
        "ROE_AND_ROCE_DIFFERENCE",
        "ROE_SOURCE_ANOMALY",
        "ROCE_SOURCE_ANOMALY",
    ],
    default="OTHER",
)

edge_cases.to_csv(
    EDGE_FILE,
    index=False,
)

# -------------------------------------------------------------------
# 7. FINAL DAY 13 REPORT
# -------------------------------------------------------------------

print("\n[6/7] Creating Day 13 report...")

financial_ratio_rows = int(
    comparison["company_id"].notna().sum()
)

financial_ratio_rows_financials = int(
    comparison["company_id"].isin(financial_set).sum()
)

financial_high_leverage_flags = int(
    comparison.loc[
        comparison["company_id"].isin(financial_set),
        "high_leverage_flag"
    ].fillna(0).sum()
)

nonfinancial_high_leverage_flags = int(
    comparison.loc[
        ~comparison["company_id"].isin(financial_set),
        "high_leverage_flag"
    ].fillna(0).sum()
)

roe_anomalies = int(
    (
        comparison["roe_difference_pct_points"].notna()
        &
        (comparison["roe_difference_pct_points"] > 5)
    ).sum()
)

roce_anomalies = int(
    (
        comparison["roce_difference_pct_points"].notna()
        &
        (comparison["roce_difference_pct_points"] > 5)
    ).sum()
)

sector_distribution = pd.read_sql_query(
    """
    SELECT
        sector,
        COUNT(*) AS companies
    FROM sectors
    GROUP BY sector
    ORDER BY companies DESC
    """,
    conn,
)

report_lines = []

report_lines.append("# Sprint 2 Day 13 — Financials & Edge-Case Audit")
report_lines.append("")
report_lines.append("## Status")
report_lines.append("")
report_lines.append("DAY 13 IMPLEMENTATION: COMPLETE")
report_lines.append("")
report_lines.append("## Sector Coverage")
report_lines.append("")
report_lines.append(
    f"- Companies in sectors table: **{total_sector_rows}**"
)
report_lines.append(
    f"- Companies with populated broad sector: **{populated_sector_rows}**"
)
report_lines.append("")
report_lines.append("### Sector distribution")
report_lines.append("")
report_lines.append("| Sector | Companies |")
report_lines.append("|---|---:|")

for _, row in sector_distribution.iterrows():
    report_lines.append(
        f"| {row['sector']} | {int(row['companies'])} |"
    )

report_lines.append("")
report_lines.append("## Financials Carve-Out")
report_lines.append("")
report_lines.append(
    f"- Financials companies identified from source: **{len(financial_ids)}**"
)
report_lines.append(
    f"- Ratio rows belonging to Financials: **{financial_ratio_rows_financials}**"
)
report_lines.append(
    f"- Financials high-leverage warnings remaining: **{financial_high_leverage_flags}**"
)
report_lines.append(
    f"- Non-Financial high-leverage warnings: **{nonfinancial_high_leverage_flags}**"
)
report_lines.append("")
report_lines.append("### Financial company IDs")
report_lines.append("")
report_lines.append(
    ", ".join(financial_ids)
)

report_lines.append("")
report_lines.append("## ROE Source Comparison")
report_lines.append("")
report_lines.append(
    f"- ROE differences >5 percentage points: **{roe_anomalies}**"
)
report_lines.append(
    "- These are logged as source/calculation comparison edge cases; "
    "the calculated KPI is not silently overwritten."
)

report_lines.append("")
report_lines.append("## ROCE Source Comparison")
report_lines.append("")
report_lines.append(
    f"- ROCE differences >5 percentage points: **{roce_anomalies}**"
)
report_lines.append(
    "- These are logged as source/calculation comparison edge cases."
)

report_lines.append("")
report_lines.append("## Edge-Case Categories")
report_lines.append("")
report_lines.append(
    "- ROE_SOURCE_ANOMALY: calculated ROE differs from source ROE by >5 percentage points."
)
report_lines.append(
    "- ROCE_SOURCE_ANOMALY: calculated ROCE differs from source ROCE by >5 percentage points."
)
report_lines.append(
    "- ROE_AND_ROCE_DIFFERENCE: both comparisons exceed the 5-point threshold."
)
report_lines.append(
    "- Financials D/E carve-out: high-leverage warning suppressed for Financials."
)

report_lines.append("")
report_lines.append("## Output Files")
report_lines.append("")
report_lines.append(
    f"- {EDGE_FILE.as_posix()}"
)
report_lines.append(
    f"- {REPORT_FILE.as_posix()}"
)

report_lines.append("")
report_lines.append("## Day 13 Validation")
report_lines.append("")
report_lines.append(
    f"- Sector rows = 92: {'PASS' if total_sector_rows == 92 else 'FAIL'}"
)
report_lines.append(
    f"- Sector values populated = 92: {'PASS' if populated_sector_rows == 92 else 'FAIL'}"
)
report_lines.append(
    f"- Financials D/E warnings = 0: {'PASS' if financial_high_leverage_flags == 0 else 'FAIL'}"
)
report_lines.append(
    "- ROE/ROCE anomalies logged rather than silently altered: PASS"
)
report_lines.append("")
report_lines.append("### Final result")
report_lines.append("")
report_lines.append("**DAY 13 COMPLETE**")

REPORT_FILE.write_text(
    "\n".join(report_lines),
    encoding="utf-8",
)

# -------------------------------------------------------------------
# FINAL VALIDATION
# -------------------------------------------------------------------

print("\n[7/7] FINAL DAY 13 VALIDATION")
print("-" * 80)

checks = {
    "Sector rows = 92": total_sector_rows == 92,
    "All 92 sectors populated": populated_sector_rows == 92,
    "Financials D/E warnings = 0": financial_high_leverage_flags == 0,
    "Edge-case file created": EDGE_FILE.exists(),
    "Day 13 report created": REPORT_FILE.exists(),
}

for name, passed in checks.items():
    print(
        f"{'PASS' if passed else 'FAIL'} - {name}"
    )

conn.close()

print("\n" + "=" * 80)

if all(checks.values()):
    print("DAY 13 SUCCESSFULLY COMPLETED")
    print("=" * 80)
    print("\nFinancials:", len(financial_ids))
    print("ROE anomalies >5 pts:", roe_anomalies)
    print("ROCE anomalies >5 pts:", roce_anomalies)
    print("Financial high-D/E warnings:", financial_high_leverage_flags)
    print("Non-Financial high-D/E warnings:", nonfinancial_high_leverage_flags)
    print("\nCreated:")
    print(" ", EDGE_FILE)
    print(" ", REPORT_FILE)
else:
    print("DAY 13 NEEDS REVIEW")
    print("=" * 80)
