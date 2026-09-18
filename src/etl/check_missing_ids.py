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


def search_file(file_path, company_id, header_row):
    try:
        df = pd.read_excel(file_path, header=header_row)

        mask = df.astype(str).apply(
            lambda column: column.str.contains(
                company_id,
                case=False,
                na=False
            )
        )

        return mask.any().any()

    except Exception as error:
        print(f"ERROR reading {file_path.name}: {error}")
        return False


def main():
    files = list(RAW_DIR.glob("*.xlsx")) + list(
        SUPPORTING_DIR.glob("*.xlsx")
    )

    print("=" * 70)
    print("MISSING COMPANY ID SEARCH")
    print("=" * 70)

    for company_id in MISSING_IDS:
        print(f"\n{company_id}:")

        found = False

        for file_path in files:

            if file_path.parent == RAW_DIR:
                header_row = 1
            else:
                header_row = 0

            if search_file(file_path, company_id, header_row):
                print(f"  FOUND -> {file_path.name}")
                found = True

        if not found:
            print("  NOT FOUND in any source file")

    print("\n" + "=" * 70)
    print("SEARCH COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()