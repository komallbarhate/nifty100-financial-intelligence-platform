import pandas as pd
from pathlib import Path

path = Path("data/supporting/1788501621129-8684701e-sectors.xlsx")

print("=" * 70)
print("DAY 13 — RAW SECTOR SOURCE INSPECTION")
print("=" * 70)

print("\nFILE:", path)
print("EXISTS:", path.exists())

df = pd.read_excel(path, header=0)

print("\nSHAPE:", df.shape)
print("\nCOLUMNS:")
for i, col in enumerate(df.columns):
    print(i, repr(col))

print("\nFIRST 20 ROWS:")
print(df.head(20).to_string(index=False))

print("\nNON-NULL COUNTS:")
print(df.notna().sum().to_string())

print("\nUNIQUE VALUES BY COLUMN:")
for col in df.columns:
    print("\n---", col, "---")
    print(df[col].dropna().astype(str).drop_duplicates().head(30).to_list())

print("\n" + "=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)
