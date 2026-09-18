from pathlib import Path
import pandas as pd

from normaliser import normalize_dataframe


# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Data folders
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SUPPORTING_DIR = PROJECT_ROOT / "data" / "supporting"


def find_excel_file(folder, keyword):
    """
    Find an Excel file in a folder whose filename contains the keyword.
    """

    files = list(folder.glob("*.xlsx"))

    matches = [
        file
        for file in files
        if keyword.lower() in file.name.lower()
    ]

    if not matches:
        raise FileNotFoundError(
            f"No Excel file containing '{keyword}' found in {folder}"
        )

    if len(matches) > 1:
        print(
            f"Warning: Multiple files found for '{keyword}'. "
            f"Using {matches[0].name}"
        )

    return matches[0]


def load_excel(folder, keyword, header_row=0):
    """
    Locate and load an Excel file using the specified header row.
    """

    file_path = find_excel_file(folder, keyword)

    print(f"\nLoading: {file_path.name}")

    df = pd.read_excel(
        file_path,
        header=header_row
    )

    print(f"Rows: {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")

    return df


def normalise_columns(df):
    """
    Standardise column names.
    """

    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
        .str.replace("&", "and", regex=False)
    )

    return df


def load_core_data():
    """
    Load the 7 core datasets.

    These files have their actual headers on Excel row 2.
    """

    datasets = {}

    datasets["analysis"] = load_excel(
        RAW_DIR,
        "analysis",
        header_row=1
    )

    datasets["balancesheet"] = load_excel(
        RAW_DIR,
        "balancesheet",
        header_row=1
    )

    datasets["cashflow"] = load_excel(
        RAW_DIR,
        "cashflow",
        header_row=1
    )

    datasets["companies"] = load_excel(
        RAW_DIR,
        "companies",
        header_row=1
    )

    datasets["documents"] = load_excel(
        RAW_DIR,
        "documents",
        header_row=1
    )

    datasets["profitandloss"] = load_excel(
        RAW_DIR,
        "profitandloss",
        header_row=1
    )

    datasets["prosandcons"] = load_excel(
        RAW_DIR,
        "prosandcons",
        header_row=1
    )

    return datasets


def load_supporting_data():
    """
    Load the 5 supporting datasets.

    These files have their actual headers on Excel row 1.
    """

    datasets = {}

    datasets["financial_ratios"] = load_excel(
        SUPPORTING_DIR,
        "financial_ratios",
        header_row=0
    )

    datasets["market_cap"] = load_excel(
        SUPPORTING_DIR,
        "market_cap",
        header_row=0
    )

    datasets["peer_groups"] = load_excel(
        SUPPORTING_DIR,
        "peer_groups",
        header_row=0
    )

    datasets["sectors"] = load_excel(
        SUPPORTING_DIR,
        "sectors",
        header_row=0
    )

    datasets["stock_prices"] = load_excel(
        SUPPORTING_DIR,
        "stock_prices",
        header_row=0
    )

    return datasets


def prepare_dataset(name, df):
    """
    Normalise column names and common fields.
    """

    print(f"\nPreparing dataset: {name}")

    df = normalise_columns(df)

    df = normalize_dataframe(df)

    print("Columns:")
    print(list(df.columns))

    print("\nFirst 3 rows:")
    print(df.head(3).to_string(index=False))

    return df


def main():
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
        **supporting_data
    }

    print("\n" + "=" * 70)
    print("NORMALISING DATASETS")
    print("=" * 70)

    prepared_data = {}

    for name, df in all_data.items():
        prepared_data[name] = prepare_dataset(
            name,
            df
        )

    print("\n" + "=" * 70)
    print("LOAD SUMMARY")
    print("=" * 70)

    for name, df in prepared_data.items():
        print(
            f"{name:20} "
            f"{df.shape[0]:6} rows x "
            f"{df.shape[1]:3} columns"
        )

    print("\nDay 2 Excel loading completed successfully.")


if __name__ == "__main__":
    main()