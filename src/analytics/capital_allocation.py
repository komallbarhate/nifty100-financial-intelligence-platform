from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

PATTERN_PATH = OUTPUT_DIR / "capital_allocation_history.csv"
CHANGE_PATH = OUTPUT_DIR / "pattern_changes.csv"


# ============================================================
# CAPITAL ALLOCATION CLASSIFIER
# ============================================================

def classify_pattern(
    cfo,
    cfi,
    cff,
    borrowing_change
):

    if pd.isna(cfo) or pd.isna(cfi) or pd.isna(cff):
        return "Insufficient Data"

    # 1
    if (
        cfo > 0
        and cfi < 0
        and cff < 0
    ):
        return "Reinvestment + Deleveraging"

    # 2
    if (
        cfo > 0
        and cfi < 0
        and cff > 0
    ):
        return "Growth + External Financing"

    # 3
    if (
        cfo > 0
        and cfi > 0
        and cff < 0
    ):
        return "Cash Generation + Deleveraging"

    # 4
    if (
        cfo > 0
        and cfi > 0
        and cff > 0
    ):
        return "Strong Cash Generation"

    # 5
    if (
        cfo < 0
        and cff > 0
    ):
        return "Financing Supported"

    # 6
    if (
        cfo < 0
        and cfi < 0
    ):
        return "Cash Burn + Investment"

    # 7
    if (
        cfo > 0
        and abs(cfi) < 1e-9
    ):
        return "Operating Cash Generation"

    # 8
    if (
        not pd.isna(borrowing_change)
        and borrowing_change < 0
        and cff < 0
    ):
        return "Deleveraging"

    return "Mixed"


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    conn = sqlite3.connect(
        DB_PATH
    )

    companies = pd.read_sql_query(
        """
        SELECT
            id,
            company_name
        FROM companies
        """,
        conn
    )

    sectors = pd.read_sql_query(
        """
        SELECT
            company_id,
            sector
        FROM sectors
        """,
        conn
    )

    cashflow = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            operating_activity,
            investing_activity,
            financing_activity
        FROM cashflow
        """,
        conn
    )

    balancesheet = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            borrowings
        FROM balancesheet
        """,
        conn
    )

    conn.close()

    return (
        companies,
        sectors,
        cashflow,
        balancesheet,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("NIFTY 100 CAPITAL ALLOCATION ANALYSIS")
    print("=" * 70)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    (
        companies,
        sectors,
        cashflow,
        balancesheet,
    ) = load_data()

    print(
        f"\nCompanies    : {len(companies)}"
    )

    print(
        f"Cash Flow    : {len(cashflow)} rows"
    )

    print(
        f"Balance Sheet: {len(balancesheet)} rows"
    )

    # ========================================================
    # TYPES
    # ========================================================

    cashflow["year"] = pd.to_numeric(
        cashflow["year"],
        errors="coerce"
    )

    balancesheet["year"] = pd.to_numeric(
        balancesheet["year"],
        errors="coerce"
    )

    for column in [
        "operating_activity",
        "investing_activity",
        "financing_activity",
    ]:

        cashflow[column] = pd.to_numeric(
            cashflow[column],
            errors="coerce"
        )

    balancesheet["borrowings"] = pd.to_numeric(
        balancesheet["borrowings"],
        errors="coerce"
    )

    sectors = sectors.drop_duplicates(
        subset=["company_id"]
    )

    # ========================================================
    # COMPANY / SECTOR MAP
    # ========================================================

    company_info = companies.merge(
        sectors,
        left_on="id",
        right_on="company_id",
        how="left"
    )

    company_info["sector"] = (
        company_info["sector"]
        .fillna("Unknown")
    )

    # ========================================================
    # BUILD YEARLY PATTERNS
    # ========================================================

    history_rows = []

    company_ids = (
        companies["id"]
        .astype(str)
        .str.strip()
        .unique()
    )

    for company_id in company_ids:

        cf = cashflow[
            cashflow["company_id"].astype(str).str.strip()
            == str(company_id).strip()
        ].copy()

        bs = balancesheet[
            balancesheet["company_id"].astype(str).str.strip()
            == str(company_id).strip()
        ].copy()

        if cf.empty:
            continue

        cf = cf.sort_values(
            "year"
        )

        bs = bs.sort_values(
            "year"
        )

        company_row = company_info[
            company_info["id"].astype(str).str.strip()
            == str(company_id).strip()
        ]

        if company_row.empty:
            company_name = company_id
            sector = "Unknown"
        else:
            company_name = company_row.iloc[0][
                "company_name"
            ]

            sector = company_row.iloc[0][
                "sector"
            ]

        previous_borrowings = np.nan

        for _, row in cf.iterrows():

            year = row["year"]

            cfo = row[
                "operating_activity"
            ]

            cfi = row[
                "investing_activity"
            ]

            cff = row[
                "financing_activity"
            ]

            # Find balance-sheet borrowings for same year.
            year_bs = bs[
                bs["year"] == year
            ]

            current_borrowings = np.nan

            if not year_bs.empty:
                current_borrowings = (
                    year_bs.iloc[-1][
                        "borrowings"
                    ]
                )

            borrowing_change = np.nan

            if (
                not pd.isna(previous_borrowings)
                and not pd.isna(current_borrowings)
            ):
                borrowing_change = (
                    current_borrowings
                    - previous_borrowings
                )

            pattern = classify_pattern(
                cfo,
                cfi,
                cff,
                borrowing_change
            )

            history_rows.append({
                "company_id": company_id,
                "company_name": company_name,
                "sector": sector,
                "year": year,
                "operating_cash_flow": cfo,
                "investing_cash_flow": cfi,
                "financing_cash_flow": cff,
                "borrowings": current_borrowings,
                "borrowing_change": borrowing_change,
                "capital_allocation_pattern": pattern,
            })

            if not pd.isna(current_borrowings):
                previous_borrowings = (
                    current_borrowings
                )

    # ========================================================
    # HISTORY DATAFRAME
    # ========================================================

    history = pd.DataFrame(
        history_rows
    )

    if history.empty:
        raise RuntimeError(
            "No capital allocation records were generated."
        )

    history = history.sort_values(
        [
            "company_id",
            "year",
        ]
    ).reset_index(
        drop=True
    )

    # ========================================================
    # SAVE COMPLETE HISTORY
    # ========================================================

    history.to_csv(
        PATTERN_PATH,
        index=False
    )

    # ========================================================
    # PATTERN CHANGES
    # ========================================================

    change_rows = []

    for company_id, group in history.groupby(
        "company_id"
    ):

        group = group.sort_values(
            "year"
        ).copy()

        valid = group[
            group[
                "capital_allocation_pattern"
            ]
            != "Insufficient Data"
        ].copy()

        if len(valid) < 2:
            continue

        previous = valid.iloc[-2]
        latest = valid.iloc[-1]

        previous_pattern = previous[
            "capital_allocation_pattern"
        ]

        latest_pattern = latest[
            "capital_allocation_pattern"
        ]

        changed = (
            previous_pattern
            != latest_pattern
        )

        change_rows.append({
            "company_id": company_id,
            "company_name": latest[
                "company_name"
            ],
            "sector": latest[
                "sector"
            ],
            "previous_year": previous[
                "year"
            ],
            "previous_pattern": previous_pattern,
            "latest_year": latest[
                "year"
            ],
            "latest_pattern": latest_pattern,
            "pattern_changed": changed,
        })

    changes = pd.DataFrame(
        change_rows
    )

    if not changes.empty:

        changes = changes.sort_values(
            "company_id"
        ).reset_index(
            drop=True
        )

    changes.to_csv(
        CHANGE_PATH,
        index=False
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    expected_patterns = [
        "Reinvestment + Deleveraging",
        "Growth + External Financing",
        "Cash Generation + Deleveraging",
        "Strong Cash Generation",
        "Financing Supported",
        "Cash Burn + Investment",
        "Operating Cash Generation",
        "Deleveraging",
    ]

    company_count = history[
        "company_id"
    ].nunique()

    years_per_company = (
        history.groupby(
            "company_id"
        )["year"]
        .nunique()
    )

    print("\n" + "=" * 70)
    print("CAPITAL ALLOCATION OUTPUT")
    print("=" * 70)

    print(
        f"Companies represented : "
        f"{company_count}"
    )

    print(
        f"92 companies complete : "
        f"{company_count == 92}"
    )

    print(
        f"Total yearly records  : "
        f"{len(history)}"
    )

    print(
        f"Minimum years/company : "
        f"{years_per_company.min()}"
    )

    print(
        f"Maximum years/company : "
        f"{years_per_company.max()}"
    )

    print("\nPattern distribution across all years:")

    print(
        history[
            "capital_allocation_pattern"
        ]
        .value_counts()
        .to_string()
    )

    print("\nEight defined patterns:")

    for pattern in expected_patterns:

        count = (
            history[
                "capital_allocation_pattern"
            ]
            == pattern
        ).sum()

        print(
            f"  {pattern:<35} {count}"
        )

    print(
        "\nLatest-year pattern distribution:"
    )

    latest_rows = (
        history
        .sort_values("year")
        .groupby(
            "company_id",
            as_index=False
        )
        .tail(1)
    )

    print(
        latest_rows[
            "capital_allocation_pattern"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nCompanies with pattern changes: "
        f"{changes['pattern_changed'].sum() if not changes.empty else 0}"
    )

    print("\nOutput files:")

    print(
        f"  {PATTERN_PATH}"
    )

    print(
        f"  {CHANGE_PATH}"
    )

    print("\nCAPITAL ALLOCATION ANALYSIS COMPLETE")


if __name__ == "__main__":
    main()