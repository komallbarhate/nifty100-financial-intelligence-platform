from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

SUMMARY_PATH = OUTPUT_DIR / "valuation_summary.xlsx"
FLAGS_PATH = OUTPUT_DIR / "valuation_flags.csv"


def find_column(df, candidates):
    for column in candidates:
        if column in df.columns:
            return column
    return None


def load_data():
    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query(
        """
        SELECT id AS company_id, company_name
        FROM companies
        """,
        conn
    )

    sectors = pd.read_sql_query(
        """
        SELECT company_id, sector
        FROM sectors
        """,
        conn
    )

    ratios = pd.read_sql_query(
        """
        SELECT *
        FROM financial_ratios
        """,
        conn
    )

    market_cap = pd.read_sql_query(
        """
        SELECT *
        FROM market_cap
        """,
        conn
    )

    conn.close()

    return companies, sectors, ratios, market_cap


def main():

    print("=" * 70)
    print("NIFTY 100 VALUATION ENGINE")
    print("=" * 70)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    companies, sectors, ratios, market_cap = load_data()

    print(f"\nCompanies loaded : {len(companies)}")
    print(f"Ratio rows       : {len(ratios)}")
    print(f"Market cap rows  : {len(market_cap)}")

    # =====================================================
    # DETECT COLUMNS
    # =====================================================

    ratio_year_col = find_column(
        ratios,
        ["year"]
    )

    fcf_col = find_column(
        ratios,
        [
            "free_cash_flow_cr",
            "free_cash_flow",
            "fcf_cr",
            "fcf"
        ]
    )

    market_year_col = find_column(
        market_cap,
        ["year"]
    )

    market_cap_col = find_column(
        market_cap,
        [
            "market_cap_crore",
            "market_cap",
            "market_cap_cr"
        ]
    )

    pe_col = find_column(
        market_cap,
        [
            "pe_ratio",
            "pe",
            "p_e_ratio"
        ]
    )

    pb_col = find_column(
        market_cap,
        [
            "pb_ratio",
            "pb",
            "p_b_ratio"
        ]
    )

    ev_col = find_column(
        market_cap,
        [
            "ev_ebitda",
            "ev_to_ebitda",
            "ev_ebitda_ratio"
        ]
    )

    print("\nDetected columns:")
    print(f"FCF column         : {fcf_col}")
    print(f"Ratio year         : {ratio_year_col}")
    print(f"Market cap column  : {market_cap_col}")
    print(f"Market cap year    : {market_year_col}")
    print(f"P/E column         : {pe_col}")
    print(f"P/B column         : {pb_col}")
    print(f"EV/EBITDA column   : {ev_col}")

    if ratio_year_col is None:
        raise ValueError(
            "Could not find year in financial_ratios."
        )

    if fcf_col is None:
        raise ValueError(
            "Could not find Free Cash Flow in financial_ratios."
        )

    if market_year_col is None:
        raise ValueError(
            "Could not find year in market_cap."
        )

    if market_cap_col is None:
        raise ValueError(
            "Could not find market cap in market_cap."
        )

    if pe_col is None:
        raise ValueError(
            "Could not find P/E in market_cap."
        )

    # =====================================================
    # CLEAN FINANCIAL RATIOS
    # =====================================================

    ratios[ratio_year_col] = pd.to_numeric(
        ratios[ratio_year_col],
        errors="coerce"
    )

    ratios[fcf_col] = pd.to_numeric(
        ratios[fcf_col],
        errors="coerce"
    )

    ratios = ratios.dropna(
        subset=["company_id", ratio_year_col]
    ).copy()

    ratios = ratios.sort_values(
        ["company_id", ratio_year_col]
    )

    # =====================================================
    # LATEST FCF PER COMPANY
    # =====================================================

    latest_ratios = (
        ratios
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    latest_ratios = latest_ratios[
        [
            "company_id",
            ratio_year_col,
            fcf_col
        ]
    ].rename(
        columns={
            ratio_year_col: "latest_ratio_year",
            fcf_col: "FCF"
        }
    )

    # =====================================================
    # MARKET DATA CLEANING
    # =====================================================

    market_cap[market_year_col] = pd.to_numeric(
        market_cap[market_year_col],
        errors="coerce"
    )

    for column in [
        market_cap_col,
        pe_col,
        pb_col,
        ev_col
    ]:
        if column is not None:
            market_cap[column] = pd.to_numeric(
                market_cap[column],
                errors="coerce"
            )

    market_cap = market_cap.dropna(
        subset=["company_id", market_year_col]
    ).copy()

    market_cap = market_cap.sort_values(
        ["company_id", market_year_col]
    )

    # =====================================================
    # LATEST MARKET DATA PER COMPANY
    # =====================================================

    latest_market = (
        market_cap
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    market_columns = [
        "company_id",
        market_year_col,
        market_cap_col,
        pe_col
    ]

    if pb_col is not None:
        market_columns.append(pb_col)

    if ev_col is not None:
        market_columns.append(ev_col)

    latest_market = latest_market[
        market_columns
    ].rename(
        columns={
            market_year_col: "market_cap_year",
            market_cap_col: "market_cap_crore",
            pe_col: "P/E"
        }
    )

    if pb_col is not None:
        latest_market = latest_market.rename(
            columns={
                pb_col: "P/B"
            }
        )
    else:
        latest_market["P/B"] = np.nan

    if ev_col is not None:
        latest_market = latest_market.rename(
            columns={
                ev_col: "EV/EBITDA"
            }
        )
    else:
        latest_market["EV/EBITDA"] = np.nan

    # =====================================================
    # 5-YEAR MEDIAN P/E
    # =====================================================

    pe_history = market_cap[
        [
            "company_id",
            market_year_col,
            pe_col
        ]
    ].copy()

    pe_history[pe_col] = pd.to_numeric(
        pe_history[pe_col],
        errors="coerce"
    )

    pe_history.loc[
        pe_history[pe_col] <= 0,
        pe_col
    ] = np.nan

    pe_history = pe_history.dropna(
        subset=[pe_col]
    )

    pe_history = pe_history.sort_values(
        ["company_id", market_year_col]
    )

    latest_five_pe = (
        pe_history
        .groupby(
            "company_id",
            group_keys=False
        )
        .tail(5)
    )

    median_pe = (
        latest_five_pe
        .groupby("company_id")[pe_col]
        .median()
        .reset_index()
        .rename(
            columns={
                pe_col: "5yr_median_PE"
            }
        )
    )

    # =====================================================
    # BUILD BASE DATASET
    # =====================================================

    valuation = companies.merge(
        sectors,
        on="company_id",
        how="left"
    )

    valuation = valuation.merge(
        latest_ratios,
        on="company_id",
        how="left"
    )

    valuation = valuation.merge(
        latest_market,
        on="company_id",
        how="left"
    )

    valuation = valuation.merge(
        median_pe,
        on="company_id",
        how="left"
    )

    valuation["sector"] = (
        valuation["sector"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    # =====================================================
    # FCF YIELD
    # =====================================================

    valuation["FCF_yield_pct"] = np.where(
        (
            valuation["market_cap_crore"].notna()
            & (valuation["market_cap_crore"] > 0)
            & valuation["FCF"].notna()
        ),
        (
            valuation["FCF"]
            / valuation["market_cap_crore"]
            * 100
        ),
        np.nan
    )

    # =====================================================
    # SECTOR MEDIAN P/E
    # =====================================================

    valid_pe = valuation[
        valuation["P/E"].notna()
        & (valuation["P/E"] > 0)
    ].copy()

    sector_medians = (
        valid_pe
        .groupby("sector")["P/E"]
        .median()
        .reset_index()
        .rename(
            columns={
                "P/E": "sector_median_PE"
            }
        )
    )

    valuation = valuation.merge(
        sector_medians,
        on="sector",
        how="left"
    )

    # =====================================================
    # P/E VS SECTOR MEDIAN
    # =====================================================

    valuation["PE_vs_sector_median_pct"] = np.where(
        (
            valuation["P/E"].notna()
            & valuation["sector_median_PE"].notna()
            & (valuation["sector_median_PE"] > 0)
        ),
        (
            (
                valuation["P/E"]
                / valuation["sector_median_PE"]
            ) - 1
        ) * 100,
        np.nan
    )

    # =====================================================
    # VALUATION FLAG
    # =====================================================

    def get_flag(row):

        pe = row["P/E"]
        sector_pe = row["sector_median_PE"]

        if (
            pd.isna(pe)
            or pd.isna(sector_pe)
            or pe <= 0
            or sector_pe <= 0
        ):
            return "N/A"

        if pe > sector_pe * 1.5:
            return "Caution"

        if pe < sector_pe * 0.7:
            return "Discount"

        return "Fair"

    valuation["flag"] = valuation.apply(
        get_flag,
        axis=1
    )

    # =====================================================
    # FINAL OUTPUT
    # =====================================================

    output_columns = [
        "company_id",
        "company_name",
        "sector",
        "P/E",
        "P/B",
        "EV/EBITDA",
        "FCF_yield_pct",
        "5yr_median_PE",
        "PE_vs_sector_median_pct",
        "flag"
    ]

    output = valuation[
        output_columns
    ].copy()

    numeric_output_columns = [
        "P/E",
        "P/B",
        "EV/EBITDA",
        "FCF_yield_pct",
        "5yr_median_PE",
        "PE_vs_sector_median_pct"
    ]

    for column in numeric_output_columns:
        output[column] = pd.to_numeric(
            output[column],
            errors="coerce"
        )

    output = output.sort_values(
        [
            "sector",
            "company_name"
        ]
    ).reset_index(drop=True)

    # =====================================================
    # SAVE EXCEL
    # =====================================================

    output.to_excel(
        SUMMARY_PATH,
        index=False
    )

    # =====================================================
    # SAVE FLAGS CSV
    # =====================================================

    flags = output[
        output["flag"].isin(
            [
                "Caution",
                "Discount"
            ]
        )
    ].copy()

    flags.to_csv(
        FLAGS_PATH,
        index=False
    )

    # =====================================================
    # VERIFICATION
    # =====================================================

    print("\n" + "=" * 70)
    print("VALUATION OUTPUT")
    print("=" * 70)

    print(
        f"Rows in summary : {len(output)}"
    )

    print(
        f"Columns         : {len(output.columns)}"
    )

    print(
        f"Caution         : "
        f"{(output['flag'] == 'Caution').sum()}"
    )

    print(
        f"Discount        : "
        f"{(output['flag'] == 'Discount').sum()}"
    )

    print(
        f"Fair            : "
        f"{(output['flag'] == 'Fair').sum()}"
    )

    print(
        f"N/A             : "
        f"{(output['flag'] == 'N/A').sum()}"
    )

    print("\nRequired columns:")

    for column in output_columns:
        print(f"  [OK] {column}")

    print("\nFiles created:")

    print(
        f"  {SUMMARY_PATH}"
    )

    print(
        f"  {FLAGS_PATH}"
    )

    print("\nFirst 10 rows:")

    print(
        output.head(10).to_string(
            index=False
        )
    )

    print("\n" + "=" * 70)
    print("VALUATION ENGINE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
