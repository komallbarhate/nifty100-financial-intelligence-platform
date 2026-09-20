from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = PROJECT_ROOT / "data" / "raw" / "market_cap.xlsx"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "market_cap_fixed.csv"


def main():
    """Fix market-cap company ID references and save the processed dataset."""
    source_path = SOURCE_PATH

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    df = pd.read_excel(source_path, header=0)

    if "company_id" not in df.columns:
        raise ValueError("Expected company_id column was not found.")

    df["company_id"] = df["company_id"].astype(str).str.strip().str.upper()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved: {OUTPUT_PATH}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")


if __name__ == "__main__":
    main()
