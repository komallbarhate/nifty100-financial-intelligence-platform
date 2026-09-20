from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
SUPPORTING_DIR = PROJECT_ROOT / "data" / "supporting"

MISSING_IDS = [
    "ULTRACEMCO",
    "UNIONBANK",
    "WIPRO",
    "ZYDUSLIFE",
    "VEDL",
    "UNITDSPR",
    "VBL",
    "ZOMATO",
]

FILES = [
    "balancesheet",
    "cashflow",
    "profitandloss",
    "financial_ratios",
]


def find_file(folder, keyword):
    """Find file."""
    matches = [
        file for file in folder.glob("*.xlsx") if keyword.lower() in file.name.lower()
    ]

    if not matches:
        return None

    return matches[0]


def inspect_company(file_path, company_id, header_row):
    """Process inspect company."""
    df = pd.read_excel(file_path, header=header_row)

    possible_id_columns = [
        column
        for column in df.columns
        if any(
            word in str(column).lower()
            for word in ["company", "ticker", "symbol", "code"]
        )
    ]

    found_rows = pd.DataFrame()

    for column in possible_id_columns:
        mask = df[column].astype(str).str.strip().str.upper() == company_id

        if mask.any():
            found_rows = df.loc[mask].copy()
            break

    return found_rows


def main():
    """Run the main workflow."""
    print("=" * 80)
    print("INSPECTING DQ-03 MISSING COMPANY IDs")
    print("=" * 80)

    for company_id in MISSING_IDS:

        print("\n" + "-" * 80)
        print(f"COMPANY ID: {company_id}")
        print("-" * 80)

        displayed = False

        for keyword in FILES:

            if keyword == "financial_ratios":
                file_path = find_file(SUPPORTING_DIR, keyword)
                header_row = 0
            else:
                file_path = find_file(RAW_DIR, keyword)
                header_row = 1

            if file_path is None:
                continue

            rows = inspect_company(file_path, company_id, header_row)

            if not rows.empty:
                displayed = True

                print(f"\nSOURCE: {file_path.name}")
                print("Columns:")
                print(list(rows.columns))

                print("\nMatching rows:")

                print(rows.head(3).to_string(index=False))

        if not displayed:
            print("No matching rows found.")

    print("\n" + "=" * 80)
    print("INSPECTION COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()
