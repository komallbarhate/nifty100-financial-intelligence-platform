from pathlib import Path

import pandas as pd

print("=" * 70)
print("RAW SOURCE COLUMN DIAGNOSTIC")
print("=" * 70)

files = list(Path("data/raw").glob("*.xlsx"))

for file in files:
    name = file.name.lower()

    if "profitandloss" in name:
        print("\nPROFIT AND LOSS")
        print("-" * 70)
        df = pd.read_excel(file, header=1)
        print(df.columns.tolist())
        print("\nYEAR-LIKE VALUES:")
        for col in df.columns:
            if (
                "year" in str(col).lower()
                or "fy" in str(col).lower()
                or "date" in str(col).lower()
            ):
                print(col)
                print(df[col].drop_duplicates().head(30).tolist())

    if "balancesheet" in name:
        print("\nBALANCE SHEET")
        print("-" * 70)
        df = pd.read_excel(file, header=1)
        print(df.columns.tolist())

        print("\nFIRST 5 ROWS:")
        print(df.head().to_string())

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
