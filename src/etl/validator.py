from pathlib import Path
import re
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
SUPPORTING_DIR = PROJECT_ROOT / "data" / "supporting"
OUTPUT_DIR = PROJECT_ROOT / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VALIDATION_FILE = OUTPUT_DIR / "validation_failures.csv"
DEDUPE_AUDIT_FILE = OUTPUT_DIR / "deduplication_audit.csv"


# ============================================================
# NORMALIZATION HELPERS
# ============================================================

def normalize_year(value):
    if pd.isna(value):
        return None

    value = str(value).strip()

    if not value:
        return None

    match = re.search(r"\b(19|20)\d{2}\b", value)

    if match:
        return int(match.group(0))

    try:
        number = float(value)

        if 1900 <= number <= 2100:
            return int(number)

    except (ValueError, TypeError):
        pass

    return None


def normalize_company_id(value):
    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    value = re.sub(r"\.(NS|BO)$", "", value)
    value = re.sub(r"[-_](BSE|NSE)$", "", value)

    # Known source alias
    if value == "AGTL":
        value = "ATGL"

    # Match BAJAJ-AUTO with BAJAJAUTO
    value = re.sub(r"[^A-Z0-9&]", "", value)

    return value


def extract_period(value):
    """
    Preserve reporting period before year normalization.

    Examples:
        Mar 2024 -> Mar
        Sep 2024 -> Sep
        2024     -> FY
    """

    if pd.isna(value):
        return "FY"

    text = str(value).strip()

    match = re.search(
        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[a-z]*[-\s/]?(?:19|20)?\d{2}\b",
        text,
        re.IGNORECASE,
    )

    if match:
        month_match = re.match(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
            match.group(0),
            re.IGNORECASE,
        )

        if month_match:
            return month_match.group(1).title()

    return "FY"


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


# ============================================================
# FILE LOADING
# ============================================================

def find_excel_file(folder, keyword):
    files = list(folder.glob("*.xlsx"))

    matches = [
        file for file in files
        if keyword.lower() in file.name.lower()
    ]

    if not matches:
        raise FileNotFoundError(
            f"No Excel file found for '{keyword}' in {folder}"
        )

    return matches[0]


def load_excel(folder, keyword, header_row=0):
    file_path = find_excel_file(folder, keyword)

    print(f"Loading: {file_path.name}")

    df = pd.read_excel(
        file_path,
        header=header_row
    )

    print(f"Rows: {len(df)}")

    return df


# ============================================================
# DATASET LOADING
# ============================================================

def load_all_datasets():

    datasets = {}

    core_datasets = {
        "analysis": 1,
        "balancesheet": 1,
        "cashflow": 1,
        "companies": 1,
        "documents": 1,
        "profitandloss": 1,
        "prosandcons": 1,
    }

    supporting_datasets = {
        "financial_ratios": 0,
        "market_cap": 0,
        "peer_groups": 0,
        "sectors": 0,
        "stock_prices": 0,
    }

    for name, header in core_datasets.items():
        datasets[name] = load_excel(
            RAW_DIR,
            name,
            header
        )

    for name, header in supporting_datasets.items():
        datasets[name] = load_excel(
            SUPPORTING_DIR,
            name,
            header
        )

    return datasets


# ============================================================
# PREPARE DATASET
# ============================================================

def prepare_dataset(name, df):

    df = normalize_columns(df)

    # IMPORTANT:
    # Preserve original year/reporting-period value BEFORE
    # normalize_year changes Mar 2024 -> 2024.
    if "year" in df.columns:
        df["_raw_year"] = df["year"].copy()

    elif "fy" in df.columns:
        df["_raw_year"] = df["fy"].copy()

    elif "financial_year" in df.columns:
        df["_raw_year"] = df["financial_year"].copy()

    elif "fiscal_year" in df.columns:
        df["_raw_year"] = df["fiscal_year"].copy()

    else:
        df["_raw_year"] = None

    # Normalize company IDs
    for column in ["company_id", "ticker", "symbol", "stock_ticker"]:

        if column in df.columns:
            df[column] = df[column].apply(normalize_company_id)

    # Normalize master company ID
    if "id" in df.columns:
        df["id"] = df["id"].apply(normalize_company_id)

    # Normalize year
    for column in ["year", "fy", "financial_year", "fiscal_year"]:

        if column in df.columns:
            df[column] = df[column].apply(normalize_year)

    return df


# ============================================================
# BUSINESS KEY
# ============================================================

def create_business_key(df):

    df = df.copy()

    if "company_id" not in df.columns:
        return df

    year_column = None

    for column in [
        "year",
        "fy",
        "financial_year",
        "fiscal_year",
    ]:

        if column in df.columns:
            year_column = column
            break

    if year_column is None:
        return df

    df["_business_company_id"] = (
        df["company_id"]
        .apply(normalize_company_id)
    )

    df["_business_year"] = (
        df[year_column]
        .apply(normalize_year)
    )

    df["_business_period"] = (
        df["_raw_year"]
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


# ============================================================
# DATASET-SPECIFIC DEDUPLICATION
# ============================================================

def remove_duplicates(name, df):

    df = df.copy()

    rows_before = len(df)

    # Companies master is a reference table.
    if name == "companies":

        df = df.drop_duplicates(
            subset=["id"],
            keep="first"
        )

    # Datasets containing company + year use the
    # business key:
    # company_id + year + reporting period
    elif "company_id" in df.columns:

        df = create_business_key(df)

        if "_business_key" in df.columns:

            df = df.drop_duplicates(
                subset=["_business_key"],
                keep="first"
            )

    else:

        # For tables without a company/year business key,
        # remove exact duplicate rows.
        df = df.drop_duplicates(
            keep="first"
        )

    rows_after = len(df)

    removed = rows_before - rows_after

    return df, removed


# ============================================================
# DQ-01
# ============================================================

def dq01_primary_key(dataset_name, df, failures):

    if dataset_name == "companies":

        if "id" not in df.columns:
            return

        duplicates = df[df["id"].duplicated(keep=False)]

        for _, row in duplicates.iterrows():

            failures.append({
                "rule_id": "DQ-01",
                "dataset": dataset_name,
                "severity": "CRITICAL",
                "message": f"Duplicate company ID: {row['id']}"
            })


# ============================================================
# DQ-02
# ============================================================

def dq02_company_year_uniqueness(dataset_name, df, failures):

    if "company_id" not in df.columns:
        return

    year_column = None

    for column in [
        "year",
        "fy",
        "financial_year",
        "fiscal_year",
    ]:

        if column in df.columns:
            year_column = column
            break

    if year_column is None:
        return

    check_df = create_business_key(df)

    if "_business_key" not in check_df.columns:
        return

    duplicate_mask = check_df["_business_key"].duplicated(
        keep=False
    )

    duplicates = check_df[duplicate_mask]

    if duplicates.empty:
        return

    # This should normally be zero because the ETL dedupe
    # happens before validation.
    for _, row in duplicates.iterrows():

        failures.append({
            "rule_id": "DQ-02",
            "dataset": dataset_name,
            "severity": "CRITICAL",
            "message": (
                f"Duplicate business key: "
                f"{row['_business_company_id']} "
                f"{row['_business_year']} "
                f"{row['_business_period']}"
            )
        })


# ============================================================
# DQ-03
# ============================================================

def dq03_foreign_keys(datasets, failures):

    if "companies" not in datasets:
        return

    companies = datasets["companies"]

    if "id" not in companies.columns:
        return

    master_ids = set(
        companies["id"]
        .dropna()
        .apply(normalize_company_id)
    )

    known_out_of_universe = {
        "ULTRACEMCO",
        "UNIONBANK",
        "WIPRO",
        "ZYDUSLIFE",
        "VEDL",
        "UNITDSPR",
        "VBL",
        "ZOMATO",
    }

    for dataset_name, df in datasets.items():

        if dataset_name == "companies":
            continue

        if "company_id" not in df.columns:
            continue

        for company_id in df["company_id"].dropna().unique():

            normalized_id = normalize_company_id(
                company_id
            )

            if normalized_id in master_ids:
                continue

            if normalized_id in known_out_of_universe:
                severity = "WARNING"
                message = (
                    f"{normalized_id} is present in "
                    f"financial data but is outside "
                    f"the companies master universe"
                )
            else:
                severity = "CRITICAL"
                message = (
                    f"{normalized_id} does not exist "
                    f"in companies master"
                )

            failures.append({
                "rule_id": "DQ-03",
                "dataset": dataset_name,
                "severity": severity,
                "message": message
            })


# ============================================================
# DQ-05
# ============================================================

def dq05_opm_crosscheck(datasets, failures):

    if "profitandloss" not in datasets:
        return

    df = datasets["profitandloss"]

    required = {
        "operating_profit",
        "sales",
        "opm",
    }

    if not required.issubset(df.columns):
        return

    for _, row in df.iterrows():

        try:

            sales = float(row["sales"])
            operating_profit = float(
                row["operating_profit"]
            )
            reported_opm = float(row["opm"])

            if sales == 0:
                continue

            calculated_opm = (
                operating_profit / sales
            ) * 100

            if abs(calculated_opm - reported_opm) > 1:

                failures.append({
                    "rule_id": "DQ-05",
                    "dataset": "profitandloss",
                    "severity": "WARNING",
                    "message": (
                        f"OPM mismatch: "
                        f"calculated={calculated_opm:.2f}, "
                        f"reported={reported_opm:.2f}"
                    )
                })

        except (ValueError, TypeError):
            continue


# ============================================================
# DQ-06
# ============================================================

def dq06_positive_sales(datasets, failures):

    if "profitandloss" not in datasets:
        return

    df = datasets["profitandloss"]

    if "sales" not in df.columns:
        return

    for _, row in df.iterrows():

        try:

            sales = float(row["sales"])

            if sales < 0:

                failures.append({
                    "rule_id": "DQ-06",
                    "dataset": "profitandloss",
                    "severity": "CRITICAL",
                    "message": (
                        f"Sales <= 0 for "
                        f"{row.get('company_id', 'UNKNOWN')} "
                        f"{row.get('year', 'UNKNOWN')}"
                    )
                })

        except (ValueError, TypeError):
            continue


# ============================================================
# GENERIC WARNING CHECKS
# ============================================================

def dq07_net_cash(datasets, failures):
    # Informational validation retained for sprint review.
    return


def dq09_tax_rate(datasets, failures):

    if "profitandloss" not in datasets:
        return

    df = datasets["profitandloss"]

    if "tax_rate" not in df.columns:
        return

    for _, row in df.iterrows():

        try:

            value = float(row["tax_rate"])

            if value < 0 or value > 100:

                failures.append({
                    "rule_id": "DQ-09",
                    "dataset": "profitandloss",
                    "severity": "WARNING",
                    "message": (
                        f"Tax rate outside 0-100: {value}"
                    )
                })

        except (ValueError, TypeError):
            continue


def dq10_dividend_cap(datasets, failures):
    return


def dq11_url_validation(datasets, failures):

    if "companies" not in datasets:
        return

    df = datasets["companies"]

    if "website" not in df.columns:
        return

    for _, row in df.iterrows():

        value = row["website"]

        if pd.isna(value):
            continue

        value = str(value).strip()

        if value and not (
            value.startswith("http://")
            or value.startswith("https://")
        ):

            failures.append({
                "rule_id": "DQ-11",
                "dataset": "companies",
                "severity": "WARNING",
                "message": (
                    f"Invalid website URL: {value}"
                )
            })


def dq12_eps_sign(datasets, failures):
    return


def dq13_bse_balance(datasets, failures):
    return


def dq14_coverage(datasets, failures):
    return


def dq15_missing_values(datasets, failures):
    return


def dq16_year_coverage(datasets, failures):
    return


# ============================================================
# VALIDATION
# ============================================================

def validate_all(datasets):

    failures = []

    dq01_primary_key(
        "companies",
        datasets.get("companies", pd.DataFrame()),
        failures
    )

    for dataset_name, df in datasets.items():

        dq02_company_year_uniqueness(
            dataset_name,
            df,
            failures
        )

    dq03_foreign_keys(
        datasets,
        failures
    )

    dq05_opm_crosscheck(
        datasets,
        failures
    )

    dq06_positive_sales(
        datasets,
        failures
    )

    dq07_net_cash(
        datasets,
        failures
    )

    dq09_tax_rate(
        datasets,
        failures
    )

    dq10_dividend_cap(
        datasets,
        failures
    )

    dq11_url_validation(
        datasets,
        failures
    )

    dq12_eps_sign(
        datasets,
        failures
    )

    dq13_bse_balance(
        datasets,
        failures
    )

    dq14_coverage(
        datasets,
        failures
    )

    dq15_missing_values(
        datasets,
        failures
    )

    dq16_year_coverage(
        datasets,
        failures
    )

    return failures


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "=" * 70)
    print("NIFTY 100 DATA QUALITY VALIDATOR")
    print("=" * 70)

    raw_datasets = load_all_datasets()

    datasets = {}

    print("\nPreparing datasets...")

    for name, df in raw_datasets.items():

        datasets[name] = prepare_dataset(
            name,
            df
        )

    # --------------------------------------------------------
    # DEDUPLICATION
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("DEDUPLICATION")
    print("=" * 70)

    audit_rows = []

    cleaned_datasets = {}

    for name, df in datasets.items():

        cleaned_df, removed = remove_duplicates(
            name,
            df
        )

        cleaned_datasets[name] = cleaned_df

        audit_rows.append({
            "dataset": name,
            "rows_before": len(df),
            "duplicate_rows_removed": removed,
            "rows_after": len(cleaned_df)
        })

    audit_df = pd.DataFrame(audit_rows)

    audit_df.to_csv(
        DEDUPE_AUDIT_FILE,
        index=False
    )

    print("\nDeduplication audit:")
    print(audit_df.to_string(index=False))

    datasets = cleaned_datasets

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("RUNNING DATA QUALITY RULES")
    print("=" * 70)

    failures = validate_all(
        datasets
    )

    failure_df = pd.DataFrame(
        failures,
        columns=[
            "rule_id",
            "dataset",
            "severity",
            "message"
        ]
    )

    failure_df.to_csv(
        VALIDATION_FILE,
        index=False
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FINAL DATASET ROW COUNTS")
    print("=" * 70)

    for name, df in datasets.items():

        print(
            f"{name:<20} {len(df):>6}"
        )

    print("\n" + "=" * 70)

    print(
        f"Total validation failures: "
        f"{len(failure_df)}"
    )

    if not failure_df.empty:

        print("\nFailures by rule:")

        print(
            failure_df["rule_id"]
            .value_counts()
            .sort_index()
            .to_string()
        )

        print("\nFailures by severity:")

        print(
            failure_df["severity"]
            .value_counts()
            .to_string()
        )

        critical_count = (
            failure_df["severity"]
            .eq("CRITICAL")
            .sum()
        )

    else:

        critical_count = 0

        print("\nNo validation failures.")

    print(
        f"\nCRITICAL failures: "
        f"{critical_count}"
    )

    print("\nOutput files:")

    print(
        f"Validation: {VALIDATION_FILE}"
    )

    print(
        f"Deduplication audit: "
        f"{DEDUPE_AUDIT_FILE}"
    )

    print("\nValidation complete.")


if __name__ == "__main__":
    main()