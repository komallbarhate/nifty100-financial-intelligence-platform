from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"

COMPANIES_FILE = next(
    RAW_DIR.glob("*companies.xlsx")
)

FINANCIAL_FILES = [
    next(RAW_DIR.glob("*balancesheet.xlsx")),
    next(RAW_DIR.glob("*cashflow.xlsx")),
    next(RAW_DIR.glob("*profitandloss.xlsx")),
]


def get_master_ids():
    df = pd.read_excel(
        COMPANIES_FILE,
        header=1
    )

    print("\nMASTER COLUMNS:")
    print(list(df.columns))

    ids = (
        df["id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return set(ids)


def get_financial_ids():

    all_ids = set()

    for file_path in FINANCIAL_FILES:

        df = pd.read_excel(
            file_path,
            header=1
        )

        ids = (
            df["company_id"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
        )

        unique_ids = set(ids)

        print(
            f"\n{file_path.name}"
        )

        print(
            f"Unique IDs: {len(unique_ids)}"
        )

        all_ids.update(unique_ids)

    return all_ids


def main():

    print("=" * 80)
    print("CORRECT COMPANY MASTER VS FINANCIAL DATA COMPARISON")
    print("=" * 80)

    master_ids = get_master_ids()

    financial_ids = get_financial_ids()

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(
        f"\nMaster company IDs: {len(master_ids)}"
    )

    print(
        f"Financial company IDs: {len(financial_ids)}"
    )

    common = sorted(
        master_ids & financial_ids
    )

    only_financial = sorted(
        financial_ids - master_ids
    )

    only_master = sorted(
        master_ids - financial_ids
    )

    print("\n" + "-" * 80)
    print("COMMON IDs")
    print("-" * 80)

    for company_id in common:
        print(company_id)

    print(
        f"\nTotal common: {len(common)}"
    )

    print("\n" + "-" * 80)
    print("FINANCIAL IDs NOT IN MASTER")
    print("-" * 80)

    for company_id in only_financial:
        print(company_id)

    print(
        f"\nTotal financial-only: {len(only_financial)}"
    )

    print("\n" + "-" * 80)
    print("MASTER IDs NOT IN FINANCIAL DATA")
    print("-" * 80)

    for company_id in only_master:
        print(company_id)

    print(
        f"\nTotal master-only: {len(only_master)}"
    )

    print("\n" + "=" * 80)
    print("COMPARISON COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()