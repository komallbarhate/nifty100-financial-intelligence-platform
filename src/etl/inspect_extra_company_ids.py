from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
SUPPORTING_DIR = PROJECT_ROOT / "data" / "supporting"

EXTRA_IDS = [
    "AGTL",
    "ULTRACEMCO",
    "UNIONBANK",
    "UNITDSPR",
    "VBL",
    "VEDL",
    "WIPRO",
    "ZOMATO",
    "ZYDUSLIFE",
]


def search_dataset(file_path, header_row, company_id):
    """Process search dataset."""
    try:
        df = pd.read_excel(file_path, header=header_row)

        company_columns = [
            column
            for column in df.columns
            if str(column).strip().lower() in ["company_id", "id", "ticker", "symbol"]
        ]

        for column in company_columns:

            values = df[column].dropna().astype(str).str.strip().str.upper()

            if company_id in set(values):

                count = (values == company_id).sum()

                return count

        return 0

    except Exception as error:
        print(f"ERROR: {file_path.name}: {error}")
        return 0


def main():
    """Run the main workflow."""
    print("=" * 80)
    print("EXTRA COMPANY IDs ACROSS ALL DATASETS")
    print("=" * 80)

    files = []

    for file_path in RAW_DIR.glob("*.xlsx"):
        files.append((file_path, 1))

    for file_path in SUPPORTING_DIR.glob("*.xlsx"):
        files.append((file_path, 0))

    for company_id in EXTRA_IDS:

        print("\n" + "-" * 80)
        print(f"COMPANY ID: {company_id}")
        print("-" * 80)

        total = 0

        for file_path, header_row in files:

            count = search_dataset(file_path, header_row, company_id)

            if count > 0:

                print(f"{file_path.name}: {count} rows")

                total += count

        print(f"TOTAL ROWS ACROSS DATASETS: {total}")

    print("\n" + "=" * 80)
    print("INSPECTION COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()
