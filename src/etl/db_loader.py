from pathlib import Path
import sqlite3
import re
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
SUPPORTING_DIR = PROJECT_ROOT / "data" / "supporting"
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
AUDIT_PATH = PROJECT_ROOT / "output" / "load_audit.csv"


# ============================================================
# FILE HELPERS
# ============================================================

def find_excel_file(folder, keyword):
    files = list(folder.glob("*.xlsx"))

    matches = [
        file
        for file in files
        if keyword.lower() in file.name.lower()
    ]

    if not matches:
        raise FileNotFoundError(
            f"Could not find Excel file for: {keyword}"
        )

    return matches[0]


def load_excel(folder, keyword, header):
    file_path = find_excel_file(
        folder,
        keyword
    )

    print(
        f"Loading {keyword}: "
        f"{file_path.name}"
    )

    return pd.read_excel(
        file_path,
        header=header
    )


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_columns(df):
    df = df.copy()

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
        .str.replace("&", "and", regex=False)
    )

    return df


def normalize_company_id(value):
    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    value = re.sub(
        r"\.(NS|BO)$",
        "",
        value
    )

    value = re.sub(
        r"[-_](BSE|NSE)$",
        "",
        value
    )

    if value == "AGTL":
        value = "ATGL"

    value = re.sub(
        r"[^A-Z0-9&]",
        "",
        value
    )

    return value


def normalize_year(value):
    if pd.isna(value):
        return None

    if isinstance(value, (pd.Timestamp,)):
        return int(value.year)

    value = str(value).strip()

    if not value:
        return None

    match = re.search(
        r"\b(19|20)\d{2}\b",
        value
    )

    if match:
        return int(match.group(0))

    try:
        number = float(value)

        if 1900 <= number <= 2100:
            return int(number)

    except (ValueError, TypeError):
        pass

    return None


def extract_period(value):
    if pd.isna(value):
        return "FY"

    text = str(value).strip()

    if not text:
        return "FY"

    match = re.search(
        r"\b("
        r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
        r")[a-z]*",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1).title()

    if "TTM" in text.upper():
        return "TTM"

    return "FY"


def is_annual_period(value):
    """
    Annual records are month-year records without
    partial-period suffixes.

    TTM and records such as:
        Mar 2023 15
        Mar 2016 9m
    are excluded from annual financial-year calculations.
    """

    if pd.isna(value):
        return False

    text = str(value).strip().lower()

    if not text:
        return False

    if "ttm" in text:
        return False

    if re.search(r"\b\d+\s*m\b", text):
        return False

    if re.search(r"\b\d+\s*months?\b", text):
        return False

    if re.search(r"\b\d+\s*9m\b", text):
        return False

    return bool(
        re.search(
            r"\b("
            r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
            r")[a-z]*[-\s/]?(?:19|20)?\d{2}\b",
            text,
            re.IGNORECASE
        )
    )


# ============================================================
# DATAFRAME PREPARATION
# ============================================================

def prepare_dataframe(df):
    df = normalize_columns(df)

    # --------------------------------------------------------
    # Preserve original reporting period
    # --------------------------------------------------------

    if "year" in df.columns:
        df["_raw_year"] = df["year"].copy()

        df["_period"] = (
            df["_raw_year"]
            .apply(extract_period)
        )

        df["_normalized_year"] = (
            df["_raw_year"]
            .apply(normalize_year)
        )

        df["year"] = df["_normalized_year"]

    # --------------------------------------------------------
    # Company ID normalization
    # --------------------------------------------------------

    for column in [
        "company_id",
        "ticker",
        "symbol",
        "stock_ticker"
    ]:

        if column in df.columns:
            df[column] = (
                df[column]
                .apply(normalize_company_id)
            )

    # Companies master uses id
    if "id" in df.columns:
        df["id"] = (
            df["id"]
            .apply(normalize_company_id)
        )

    # --------------------------------------------------------
    # Column aliases
    # --------------------------------------------------------

    if "equity_capital" in df.columns:
        if "share_capital" not in df.columns:
            df["share_capital"] = df["equity_capital"]

    if "other_asset" in df.columns:
        if "other_assets" not in df.columns:
            df["other_assets"] = df["other_asset"]

    if "dividend_payout" in df.columns:
        if "dividend_payout" not in df.columns:
            df["dividend_payout"] = df["dividend_payout"]

    return df


# ============================================================
# BUSINESS KEY DEDUPLICATION
# ============================================================

def add_business_key(df):
    df = df.copy()

    if "company_id" not in df.columns:
        return df

    if "_raw_year" in df.columns:
        raw_year = df["_raw_year"]
    elif "year" in df.columns:
        raw_year = df["year"]
    else:
        return df

    df["_business_company_id"] = (
        df["company_id"]
        .apply(normalize_company_id)
    )

    df["_business_year"] = (
        raw_year
        .apply(normalize_year)
    )

    df["_business_period"] = (
        raw_year
        .apply(extract_period)
    )

    df["_business_key"] = (
        df["_business_company_id"].astype(str)
        + "|"
        + df["_business_year"].astype(str)
        + "|"
        + df["_business_period"].astype(str)
    )

    return df


def deduplicate_dataframe(name, df):
    before = len(df)

    if name == "companies":

        if "id" in df.columns:
            df = df.drop_duplicates(
                subset=["id"],
                keep="first"
            )

    elif "company_id" in df.columns:

        df = add_business_key(df)

        if "_business_key" in df.columns:

            df = df.drop_duplicates(
                subset=["_business_key"],
                keep="first"
            )

    else:

        df = df.drop_duplicates(
            keep="first"
        )

    helper_columns = [
        "_business_company_id",
        "_business_year",
        "_business_period",
        "_business_key"
    ]

    df = df.drop(
        columns=[
            column
            for column in helper_columns
            if column in df.columns
        ],
        errors="ignore"
    )

    after = len(df)

    return df, before - after


# ============================================================
# DATASET LOADING
# ============================================================

def load_all_datasets():

    datasets = {}

    core = {
        "analysis": 1,
        "balancesheet": 1,
        "cashflow": 1,
        "companies": 1,
        "documents": 1,
        "profitandloss": 1,
        "prosandcons": 1,
    }

    supporting = {
        "financial_ratios": 0,
        "market_cap": 0,
        "peer_groups": 0,
        "sectors": 0,
        "stock_prices": 0,
    }

    for name, header in core.items():

        datasets[name] = prepare_dataframe(
            load_excel(
                RAW_DIR,
                name,
                header
            )
        )

    for name, header in supporting.items():

        datasets[name] = prepare_dataframe(
            load_excel(
                SUPPORTING_DIR,
                name,
                header
            )
        )

    return datasets


# ============================================================
# FILTER OUT-OF-UNIVERSE COMPANIES
# ============================================================

def filter_to_master_universe(datasets):

    master = datasets["companies"]

    master_ids = set(
        master["id"]
        .dropna()
        .apply(normalize_company_id)
    )

    filtered = {}

    for name, df in datasets.items():

        if name == "companies":
            filtered[name] = df
            continue

        if "company_id" not in df.columns:
            filtered[name] = df
            continue

        before = len(df)

        df = df[
            df["company_id"]
            .apply(normalize_company_id)
            .isin(master_ids)
        ].copy()

        removed = before - len(df)

        if removed > 0:
            print(
                f"{name}: removed "
                f"{removed} out-of-universe rows"
            )

        filtered[name] = df

    return filtered


# ============================================================
# SQLITE INSERT
# ============================================================

TABLE_COLUMNS = {

    "companies": [
        "id",
        "company_logo",
        "company_name",
        "chart_link",
        "about_company",
        "website",
        "nse_profile",
        "bse_profile",
        "face_value",
        "book_value",
        "roce_percentage",
        "roe_percentage"
    ],

    "profitandloss": [
        "id",
        "company_id",
        "year",
        "sales",
        "expenses",
        "operating_profit",
        "opm_percentage",
        "other_income",
        "interest",
        "depreciation",
        "profit_before_tax",
        "tax_percentage",
        "net_profit",
        "eps",
        "dividend_payout"
    ],

    "balancesheet": [
        "id",
        "company_id",
        "year",
        "share_capital",
        "reserves",
        "borrowings",
        "other_liabilities",
        "total_liabilities",
        "fixed_assets",
        "cwip",
        "investments",
        "other_assets",
        "total_assets"
    ],

    "cashflow": [
        "id",
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow"
    ],

    "analysis": [
        "id",
        "company_id",
        "year",
        "metric",
        "value"
    ],

    "documents": [
        "id",
        "company_id",
        "year",
        "document"
    ],

    "prosandcons": [
        "id",
        "company_id",
        "pros",
        "cons"
    ],

    "financial_ratios": [
        "id",
        "company_id",
        "year",
        "pe_ratio",
        "pb_ratio",
        "dividend_yield",
        "roce",
        "roe",
        "debt_to_equity",
        "current_ratio",
        "interest_coverage",
        "opm",
        "npm",
        "eps"
    ],

    "market_cap": [
        "id",
        "company_id",
        "date",
        "market_cap"
    ],

    "peer_groups": [
        "id",
        "company_id",
        "peer_group"
    ],

    "sectors": [
        "id",
        "company_id",
        "sector",
        "industry"
    ],

    "stock_prices": [
        "id",
        "company_id",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]
}


def clean_for_sqlite(df, columns):

    df = df.copy()

    for column in columns:

        if column not in df.columns:
            df[column] = None

    df = df[columns].copy()

    df = df.astype(object)

    df = df.where(
        pd.notna(df),
        None
    )

    return df


def insert_dataset(connection, name, df):

    columns = TABLE_COLUMNS[name]

    df = clean_for_sqlite(
        df,
        columns
    )

    placeholders = ",".join(
        ["?"] * len(columns)
    )

    column_sql = ",".join(
        [f'"{column}"' for column in columns]
    )

    sql = (
        f'INSERT INTO "{name}" '
        f'({column_sql}) '
        f'VALUES ({placeholders})'
    )

    rows = [
        tuple(row)
        for row in df.itertuples(
            index=False,
            name=None
        )
    ]

    if rows:
        connection.executemany(
            sql,
            rows
        )

    return len(rows)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("NIFTY 100 SQLITE DATA LOADER")
    print("=" * 70)

    if DB_PATH.exists():
        DB_PATH.unlink()

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DB_PATH
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    with open(
        PROJECT_ROOT / "db" / "schema.sql",
        encoding="utf-8"
    ) as file:

        schema = file.read()

    connection.executescript(schema)

    datasets = load_all_datasets()

    audit = []

    print("\n" + "=" * 70)
    print("DEDUPLICATION")
    print("=" * 70)

    cleaned = {}

    for name, df in datasets.items():

        cleaned_df, removed = (
            deduplicate_dataframe(
                name,
                df
            )
        )

        cleaned[name] = cleaned_df

        audit.append({
            "dataset": name,
            "source_rows": len(df),
            "duplicate_rows_removed": removed,
            "rows_after_deduplication": len(cleaned_df),
            "out_of_universe_rows_removed": 0,
            "rows_loaded": 0,
            "status": "PENDING"
        })

    datasets = cleaned

    print("\n" + "=" * 70)
    print("FILTERING TO MASTER UNIVERSE")
    print("=" * 70)

    datasets = filter_to_master_universe(
        datasets
    )

    for row in audit:

        name = row["dataset"]

        row["out_of_universe_rows_removed"] = (
            row["rows_after_deduplication"]
            - len(datasets[name])
        )

    # ========================================================
    # LOAD ORDER
    # ========================================================

    load_order = [
        "companies",
        "sectors",
        "peer_groups",
        "analysis",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "documents",
        "prosandcons",
        "financial_ratios",
        "market_cap",
        "stock_prices"
    ]

    print("\n" + "=" * 70)
    print("LOADING DATABASE")
    print("=" * 70)

    try:

        for name in load_order:

            rows_loaded = insert_dataset(
                connection,
                name,
                datasets[name]
            )

            for row in audit:

                if row["dataset"] == name:

                    row["rows_loaded"] = rows_loaded
                    row["status"] = "LOADED"

            print(
                f"{name:<20} "
                f"{rows_loaded:>6} rows"
            )

        connection.commit()

    except Exception as error:

        connection.rollback()

        print("\nDATABASE LOAD FAILED")
        print(str(error))

        connection.close()

        raise

    fk_result = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    print("\n" + "=" * 70)
    print("FOREIGN KEY CHECK")
    print("=" * 70)

    print(
        f"Foreign key violations: "
        f"{len(fk_result)}"
    )

    print("\n" + "=" * 70)
    print("DATABASE ROW COUNTS")
    print("=" * 70)

    for name in load_order:

        count = connection.execute(
            f'SELECT COUNT(*) FROM "{name}"'
        ).fetchone()[0]

        print(
            f"{name:<20} {count:>6}"
        )

    audit_df = pd.DataFrame(audit)

    AUDIT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    audit_df.to_csv(
        AUDIT_PATH,
        index=False
    )

    connection.close()

    print("\n" + "=" * 70)
    print("LOAD COMPLETE")
    print("=" * 70)

    print(
        f"Database: {DB_PATH}"
    )

    print(
        f"Audit: {AUDIT_PATH}"
    )

    print(
        f"Foreign key violations: "
        f"{len(fk_result)}"
    )


if __name__ == "__main__":
    main()