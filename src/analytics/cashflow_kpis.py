from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

INTELLIGENCE_PATH = OUTPUT_DIR / "cashflow_intelligence.xlsx"
DISTRESS_PATH = OUTPUT_DIR / "distress_alerts.csv"


# ============================================================
# CLASSIFICATION RULES
# ============================================================

def classify_cfo_quality(score):

    if pd.isna(score):
        return "Insufficient Data"

    if score > 1.0:
        return "High Quality"

    if score >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def classify_capex(intensity):

    if pd.isna(intensity):
        return "Insufficient Data"

    if intensity < 3:
        return "Asset Light"

    if intensity <= 8:
        return "Moderate"

    return "Capital Intensive"


def calculate_cagr(series, years):

    series = pd.to_numeric(
        series,
        errors="coerce"
    ).dropna()

    if len(series) < years + 1:
        return np.nan

    values = series.tail(
        years + 1
    )

    start = values.iloc[0]
    end = values.iloc[-1]

    if (
        pd.isna(start)
        or pd.isna(end)
        or start <= 0
        or end <= 0
    ):
        return np.nan

    return (
        (
            end / start
        ) ** (
            1 / years
        )
        - 1
    ) * 100


def calculate_fcf_conversion(cfo, pat):

    if (
        pd.isna(cfo)
        or pd.isna(pat)
        or pat == 0
    ):
        return np.nan

    return (
        cfo / pat
    ) * 100


def classify_capital_allocation(
    cfo,
    cfi,
    cff,
    borrowing_change
):

    if (
        cfo > 0
        and cfi < 0
        and cff < 0
    ):
        return "Reinvestment + Deleveraging"

    if (
        cfo > 0
        and cfi < 0
        and cff > 0
    ):
        return "Growth + External Financing"

    if (
        cfo > 0
        and cfi > 0
        and cff < 0
    ):
        return "Cash Generation + Deleveraging"

    if (
        cfo > 0
        and cfi > 0
        and cff > 0
    ):
        return "Strong Cash Generation"

    if (
        cfo < 0
        and cff > 0
    ):
        return "Financing Supported"

    if (
        cfo < 0
        and cfi < 0
    ):
        return "Cash Burn + Investment"

    if (
        cfo > 0
        and abs(cfi) < 1e-9
    ):
        return "Operating Cash Generation"

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
            financing_activity,
            net_cash_flow
        FROM cashflow
        """,
        conn
    )

    ratios = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            free_cash_flow_cr,
            cfo_pat_ratio,
            capex_cr,
            capex_intensity_pct
        FROM financial_ratios
        """,
        conn
    )

    profit_loss = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            net_profit
        FROM profitandloss
        """,
        conn
    )

    balance_sheet = pd.read_sql_query(
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
        ratios,
        profit_loss,
        balance_sheet,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("NIFTY 100 CASH FLOW INTELLIGENCE")
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
        ratios,
        profit_loss,
        balance_sheet,
    ) = load_data()

    print(
        f"\nCompanies   : {len(companies)}"
    )

    print(
        f"Sectors     : {len(sectors)} rows"
    )

    print(
        f"Cash Flow   : {len(cashflow)} rows"
    )

    print(
        f"Ratios      : {len(ratios)} rows"
    )

    print(
        f"P&L         : {len(profit_loss)} rows"
    )

    print(
        f"Balance     : {len(balance_sheet)} rows"
    )

    # ========================================================
    # PREPARE TYPES
    # ========================================================

    for df in [
        cashflow,
        ratios,
        profit_loss,
        balance_sheet,
    ]:

        df["year"] = pd.to_numeric(
            df["year"],
            errors="coerce"
        )

    for column in [
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]:

        cashflow[column] = pd.to_numeric(
            cashflow[column],
            errors="coerce"
        )

    for column in [
        "free_cash_flow_cr",
        "cfo_pat_ratio",
        "capex_cr",
        "capex_intensity_pct",
    ]:

        ratios[column] = pd.to_numeric(
            ratios[column],
            errors="coerce"
        )

    profit_loss["net_profit"] = pd.to_numeric(
        profit_loss["net_profit"],
        errors="coerce"
    )

    balance_sheet["borrowings"] = pd.to_numeric(
        balance_sheet["borrowings"],
        errors="coerce"
    )

    sectors = sectors.drop_duplicates(
        subset=["company_id"]
    )

    # ========================================================
    # COMPANY + SECTOR
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
    # PROCESS
    # ========================================================

    intelligence_rows = []
    distress_rows = []

    company_ids = (
        companies["id"]
        .astype(str)
        .str.strip()
        .unique()
    )

    for company_id in company_ids:

        company_cf = cashflow[
            cashflow["company_id"].astype(str).str.strip()
            == str(company_id).strip()
        ].copy()

        company_ratios = ratios[
            ratios["company_id"].astype(str).str.strip()
            == str(company_id).strip()
        ].copy()

        company_pl = profit_loss[
            profit_loss["company_id"].astype(str).str.strip()
            == str(company_id).strip()
        ].copy()

        company_bs = balance_sheet[
            balance_sheet["company_id"].astype(str).str.strip()
            == str(company_id).strip()
        ].copy()

        company_cf = company_cf.sort_values(
            "year"
        )

        company_ratios = company_ratios.sort_values(
            "year"
        )

        company_pl = company_pl.sort_values(
            "year"
        )

        company_bs = company_bs.sort_values(
            "year"
        )

        if company_cf.empty:
            continue

        # ----------------------------------------------------
        # COMPANY INFO
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # CFO QUALITY
        # ----------------------------------------------------

        ratio_values = company_ratios[
            "cfo_pat_ratio"
        ].dropna()

        if not ratio_values.empty:

            cfo_quality_score = (
                ratio_values
                .tail(5)
                .mean()
            )

        else:

            merged = company_cf[
                [
                    "year",
                    "operating_activity",
                ]
            ].merge(
                company_pl[
                    [
                        "year",
                        "net_profit",
                    ]
                ],
                on="year",
                how="inner"
            )

            merged["ratio"] = (
                merged["operating_activity"]
                / merged["net_profit"].replace(
                    0,
                    np.nan
                )
            )

            cfo_quality_score = (
                merged["ratio"]
                .replace(
                    [np.inf, -np.inf],
                    np.nan
                )
                .dropna()
                .tail(5)
                .mean()
            )

        cfo_quality_label = classify_cfo_quality(
            cfo_quality_score
        )

        # ----------------------------------------------------
        # LATEST CASH FLOW
        # ----------------------------------------------------

        latest_cf = company_cf.iloc[-1]

        latest_cfo = latest_cf[
            "operating_activity"
        ]

        latest_cfi = latest_cf[
            "investing_activity"
        ]

        latest_cff = latest_cf[
            "financing_activity"
        ]

        latest_year = latest_cf[
            "year"
        ]

        # ----------------------------------------------------
        # CAPEX
        # ----------------------------------------------------
        # Use the already calculated and validated
        # financial_ratios.capex_intensity_pct.

        latest_ratio = (
            company_ratios.iloc[-1]
            if not company_ratios.empty
            else None
        )

        if latest_ratio is not None:

            capex_intensity = latest_ratio[
                "capex_intensity_pct"
            ]

        else:

            capex_intensity = np.nan

        capex_label = classify_capex(
            capex_intensity
        )

        # ----------------------------------------------------
        # FCF CAGR
        # ----------------------------------------------------

        fcf_cagr_5yr = calculate_cagr(
            company_ratios[
                "free_cash_flow_cr"
            ],
            5
        )

        # ----------------------------------------------------
        # FCF CONVERSION
        # ----------------------------------------------------

        latest_pat = np.nan

        if not company_pl.empty:

            latest_pat = company_pl.iloc[-1][
                "net_profit"
            ]

        fcf_conversion_pct = (
            calculate_fcf_conversion(
                latest_cfo,
                latest_pat
            )
        )

        # ----------------------------------------------------
        # DISTRESS
        # ----------------------------------------------------

        distress_flag = bool(
            not pd.isna(latest_cfo)
            and not pd.isna(latest_cff)
            and latest_cfo < 0
            and latest_cff > 0
        )

        # ----------------------------------------------------
        # BORROWING CHANGE
        # ----------------------------------------------------

        borrowing_change = np.nan

        if len(company_bs) >= 2:

            previous_debt = company_bs.iloc[-2][
                "borrowings"
            ]

            current_debt = company_bs.iloc[-1][
                "borrowings"
            ]

            if (
                not pd.isna(previous_debt)
                and not pd.isna(current_debt)
            ):

                borrowing_change = (
                    current_debt
                    - previous_debt
                )

        # ----------------------------------------------------
        # DELEVERAGING
        # ----------------------------------------------------

        deleveraging_flag = bool(
            not pd.isna(borrowing_change)
            and borrowing_change < 0
            and latest_cff < 0
        )

        # ----------------------------------------------------
        # CAPITAL ALLOCATION
        # ----------------------------------------------------

        capital_allocation_label = (
            classify_capital_allocation(
                latest_cfo,
                latest_cfi,
                latest_cff,
                borrowing_change
            )
        )

        # ----------------------------------------------------
        # OUTPUT RECORD
        # ----------------------------------------------------

        intelligence_rows.append({
            "company_id": company_id,
            "sector": sector,
            "cfo_quality_score": (
                round(
                    cfo_quality_score,
                    4
                )
                if not pd.isna(cfo_quality_score)
                else np.nan
            ),
            "cfo_quality_label": (
                cfo_quality_label
            ),
            "capex_intensity_pct": (
                round(
                    capex_intensity,
                    2
                )
                if not pd.isna(capex_intensity)
                else np.nan
            ),
            "capex_label": capex_label,
            "fcf_cagr_5yr": (
                round(
                    fcf_cagr_5yr,
                    2
                )
                if not pd.isna(fcf_cagr_5yr)
                else np.nan
            ),
            "fcf_conversion_pct": (
                round(
                    fcf_conversion_pct,
                    2
                )
                if not pd.isna(fcf_conversion_pct)
                else np.nan
            ),
            "distress_flag": distress_flag,
            "deleveraging_flag": deleveraging_flag,
            "capital_allocation_label": (
                capital_allocation_label
            ),
        })

        # ----------------------------------------------------
        # DISTRESS CSV
        # ----------------------------------------------------

        if distress_flag:

            distress_rows.append({
                "company_id": company_id,
                "company_name": company_name,
                "sector": sector,
                "year": latest_year,
                "operating_cash_flow": latest_cfo,
                "financing_cash_flow": latest_cff,
                "net_profit": latest_pat,
            })

    # ========================================================
    # DATAFRAMES
    # ========================================================

    intelligence = pd.DataFrame(
        intelligence_rows
    )

    distress = pd.DataFrame(
        distress_rows,
        columns=[
            "company_id",
            "company_name",
            "sector",
            "year",
            "operating_cash_flow",
            "financing_cash_flow",
            "net_profit",
        ]
    )

    intelligence = intelligence.sort_values(
        "company_id"
    ).reset_index(
        drop=True
    )

    distress = distress.sort_values(
        "company_id"
    ).reset_index(
        drop=True
    )

    # ========================================================
    # EXCEL
    # ========================================================

    with pd.ExcelWriter(
        INTELLIGENCE_PATH,
        engine="openpyxl"
    ) as writer:

        intelligence.to_excel(
            writer,
            sheet_name="cashflow_intelligence",
            index=False
        )

        summary = pd.DataFrame([
            {
                "metric": "Companies",
                "value": len(intelligence),
            },
            {
                "metric": "High Quality CFO",
                "value": (
                    intelligence[
                        "cfo_quality_label"
                    ]
                    == "High Quality"
                ).sum(),
            },
            {
                "metric": "Moderate CFO",
                "value": (
                    intelligence[
                        "cfo_quality_label"
                    ]
                    == "Moderate"
                ).sum(),
            },
            {
                "metric": "Accrual Risk",
                "value": (
                    intelligence[
                        "cfo_quality_label"
                    ]
                    == "Accrual Risk"
                ).sum(),
            },
            {
                "metric": "Asset Light",
                "value": (
                    intelligence[
                        "capex_label"
                    ]
                    == "Asset Light"
                ).sum(),
            },
            {
                "metric": "Moderate CapEx",
                "value": (
                    intelligence[
                        "capex_label"
                    ]
                    == "Moderate"
                ).sum(),
            },
            {
                "metric": "Capital Intensive",
                "value": (
                    intelligence[
                        "capex_label"
                    ]
                    == "Capital Intensive"
                ).sum(),
            },
            {
                "metric": "Distress Flags",
                "value": (
                    intelligence[
                        "distress_flag"
                    ]
                    == True
                ).sum(),
            },
            {
                "metric": "Deleveraging Flags",
                "value": (
                    intelligence[
                        "deleveraging_flag"
                    ]
                    == True
                ).sum(),
            },
        ])

        summary.to_excel(
            writer,
            sheet_name="summary",
            index=False
        )

    # ========================================================
    # DISTRESS CSV
    # ========================================================

    distress.to_csv(
        DISTRESS_PATH,
        index=False
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    print("\n" + "=" * 70)
    print("CASH FLOW INTELLIGENCE OUTPUT")
    print("=" * 70)

    print(
        f"Companies processed : "
        f"{len(intelligence)}"
    )

    print(
        f"Required rows       : "
        f"{len(intelligence) == 92}"
    )

    print("\nCFO Quality:")
    print(
        intelligence[
            "cfo_quality_label"
        ]
        .value_counts()
        .to_string()
    )

    print("\nCapEx Classification:")
    print(
        intelligence[
            "capex_label"
        ]
        .value_counts()
        .to_string()
    )

    print("\nCapital Allocation:")
    print(
        intelligence[
            "capital_allocation_label"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nDistress flags      : "
        f"{intelligence['distress_flag'].sum()}"
    )

    print(
        "Deleveraging flags  : "
        f"{intelligence['deleveraging_flag'].sum()}"
    )

    print("\nOutput files:")

    print(
        f"  {INTELLIGENCE_PATH}"
    )

    print(
        f"  {DISTRESS_PATH}"
    )

    print("\nCASH FLOW INTELLIGENCE COMPLETE")


if __name__ == "__main__":
    main()