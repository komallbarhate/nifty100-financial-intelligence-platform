from pathlib import Path

import pandas as pd

from src.etl.normaliser import normalize_dataframe

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
SUPPORTING_DIR = PROJECT_ROOT / "data" / "supporting"


def load_core_data():
    """Load core data."""
    datasets = {}

    datasets["analysis"] = pd.read_excel(
        RAW_DIR / "analysis.xlsx",
        header=1,
    )

    datasets["balancesheet"] = pd.read_excel(
        RAW_DIR / "balancesheet.xlsx",
        header=1,
    )

    datasets["cashflow"] = pd.read_excel(
        RAW_DIR / "cashflow.xlsx",
        header=1,
    )

    datasets["companies"] = pd.read_excel(
        RAW_DIR / "companies.xlsx",
        header=1,
    )

    datasets["documents"] = pd.read_excel(
        RAW_DIR / "documents.xlsx",
        header=1,
    )

    datasets["profitandloss"] = pd.read_excel(
        RAW_DIR / "profitandloss.xlsx",
        header=1,
    )

    datasets["prosandcons"] = pd.read_excel(
        RAW_DIR / "prosandcons.xlsx",
        header=1,
    )

    return datasets


def load_supporting_data():
    """Load supporting data."""
    datasets = {}

    datasets["financial_ratios"] = pd.read_excel(
        SUPPORTING_DIR / "financial_ratios.xlsx",
        header=0,
    )

    datasets["market_cap"] = pd.read_excel(
        SUPPORTING_DIR / "market_cap.xlsx",
        header=0,
    )

    datasets["peer_groups"] = pd.read_excel(
        SUPPORTING_DIR / "peer_groups.xlsx",
        header=0,
    )

    datasets["sectors"] = pd.read_excel(
        SUPPORTING_DIR / "sectors.xlsx",
        header=0,
    )

    datasets["stock_prices"] = pd.read_excel(
        SUPPORTING_DIR / "stock_prices.xlsx",
        header=0,
    )

    return datasets


def prepare_dataset(name, df):
    """
    Normalise column names and common fields.
    """

    print(f"\nPreparing dataset: {name}")

    df = normalize_dataframe(df)

    # Preserve the original year/reporting-period value
    # before normalization.
    if "year" in df.columns:
        df["_raw_year"] = df["year"].copy()

    elif "fy" in df.columns:
        df["_raw_year"] = df["fy"].copy()

    elif "financial_year" in df.columns:
        df["_raw_year"] = df["financial_year"].copy()

    elif "fiscal_year" in df.columns:
        df["_raw_year"] = df["fiscal_year"].copy()

    # Normalize company identifiers.
    company_columns = [
        "company_id",
        "ticker",
        "symbol",
        "stock_ticker",
    ]

    for column in company_columns:
        if column in df.columns:
            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
                .str.upper()
                .str.replace(".NS", "", regex=False)
                .str.replace(".BO", "", regex=False)
            )

    # Normalize year fields where possible.
    for column in [
        "year",
        "fy",
        "financial_year",
        "fiscal_year",
    ]:
        if column in df.columns:
            numeric_year = pd.to_numeric(
                df[column],
                errors="coerce",
            )

            df[column] = numeric_year.astype("Int64")

    print("Columns:")
    print(list(df.columns))

    print("\nFirst 3 rows:")
    print(df.head(3).to_string(index=False))

    return df


def main():
    """Run the main workflow."""
    print("=" * 70)
    print("NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM")
    print("DAY 2 - EXCEL LOADER")
    print("=" * 70)

    print("\nLoading CORE datasets...")

    core_data = load_core_data()

    print("\n" + "=" * 70)
    print("Loading SUPPORTING datasets...")
    print("=" * 70)

    supporting_data = load_supporting_data()

    all_data = {
        **core_data,
        **supporting_data,
    }

    print("\n" + "=" * 70)
    print("NORMALISING DATASETS")
    print("=" * 70)

    prepared_data = {}

    for name, df in all_data.items():
        prepared_data[name] = prepare_dataset(
            name,
            df,
        )

    print("\n" + "=" * 70)
    print("LOAD SUMMARY")
    print("=" * 70)

    for name, df in prepared_data.items():
        print(f"{name:20} " f"{df.shape[0]:6} rows x " f"{df.shape[1]:3} columns")

    print("\nDay 2 Excel loading completed successfully.")


if __name__ == "__main__":
    main()
