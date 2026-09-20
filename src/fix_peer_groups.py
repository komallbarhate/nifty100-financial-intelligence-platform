import sqlite3

import pandas as pd

DB_PATH = "data/nifty100.db"
SOURCE_PATH = "data/supporting/1788501620796-5060f580-peer_groups.xlsx"

conn = sqlite3.connect(DB_PATH)

df = pd.read_excel(SOURCE_PATH)

df["company_id"] = df["company_id"].astype(str).str.strip().str.upper()

# Match the company ID used by our companies table.
df["company_id"] = df["company_id"].replace({"BAJAJ-AUTO": "BAJAJAUTO"})

# Clear the existing incomplete mappings.
conn.execute("UPDATE peer_groups SET peer_group = NULL")
conn.commit()

# Populate peer_group from the source file.
for _, row in df.iterrows():
    conn.execute(
        """
        UPDATE peer_groups
        SET peer_group = ?
        WHERE company_id = ?
        """,
        (row["peer_group_name"], row["company_id"]),
    )

conn.commit()

total = conn.execute("SELECT COUNT(*) FROM peer_groups").fetchone()[0]

populated = conn.execute("""
    SELECT COUNT(*)
    FROM peer_groups
    WHERE peer_group IS NOT NULL
      AND TRIM(peer_group) <> ''
    """).fetchone()[0]

groups = conn.execute("""
    SELECT peer_group, COUNT(*)
    FROM peer_groups
    WHERE peer_group IS NOT NULL
    GROUP BY peer_group
    ORDER BY peer_group
    """).fetchall()

benchmarks = conn.execute("""
    SELECT COUNT(*)
    FROM peer_groups pg
    JOIN companies c
      ON c.id = pg.company_id
    WHERE pg.peer_group IS NOT NULL
    """).fetchone()[0]

print("=" * 70)
print("PEER GROUP DATA LOAD")
print("=" * 70)
print(f"Total DB rows: {total}")
print(f"Populated peer groups: {populated}")
print(f"Distinct peer groups: {len(groups)}")
print()

for group, count in groups:
    print(f"{group}: {count}")

print()
print(f"Companies successfully matched: {benchmarks}")
print("=" * 70)

conn.close()
