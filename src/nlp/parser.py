from pathlib import Path
import re
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ANALYSIS_PATH = PROJECT_ROOT / "data" / "raw" / "analysis.xlsx"
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

PARSED_PATH = OUTPUT_DIR / "analysis_parsed.csv"
FAILURES_PATH = OUTPUT_DIR / "parse_failures.csv"
VALIDATION_PATH = OUTPUT_DIR / "analysis_cagr_validation.csv"


PATTERN = re.compile(
    r"(\d+)\s*Years?:?\s*([\d.]+)%",
    re.IGNORECASE
)


TARGETS = {
    "compounded_sales_growth": [
        "compounded_sales_growth",
        "compounded sales growth",
    ],
    "compounded_profit_growth": [
        "compounded_profit_growth",
        "compounded profit growth",
    ],
    "stock_price_cagr": [
        "stock_price_cagr",
        "stock price cagr",
    ],
    "roe": [
        "roe",
        "return on equity",
    ],
}


def normalise(value):
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(value).strip().lower()
    ).strip("_")


def find_column(columns, aliases):
    normalised_columns = {
        normalise(column): column
        for column in columns
    }

    for alias in aliases:
        alias_key = normalise(alias)

        if alias_key in normalised_columns:
            return normalised_columns[alias_key]

    for column in columns:
        column_key = normalise(column)

        for alias in aliases:
            alias_key = normalise(alias)

            if (
                alias_key in column_key
                or column_key in alias_key
            ):
                return column

    return None


def main():

    print("=" * 70)
    print("NIFTY 100 ANALYSIS TEXT PARSER")
    print("=" * 70)

    if not ANALYSIS_PATH.exists():
        raise FileNotFoundError(
            f"Analysis file not found: {ANALYSIS_PATH}"
        )

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------------
    # LOAD ANALYSIS EXCEL
    # ---------------------------------------------------------

    df = pd.read_excel(
        ANALYSIS_PATH,
        sheet_name=0,
        header=1
    )

    print(f"\nRows loaded : {len(df)}")
    print(f"Columns     : {list(df.columns)}")

    # ---------------------------------------------------------
    # FIND COMPANY ID
    # ---------------------------------------------------------

    company_col = find_column(
        df.columns,
        [
            "company_id",
            "company id",
            "id",
            "ticker",
        ]
    )

    if company_col is None:
        raise ValueError(
            "Could not identify the company ID column "
            "in analysis.xlsx."
        )

    print(f"\nCompany ID column: {company_col}")

    # ---------------------------------------------------------
    # FIND TARGET COLUMNS
    # ---------------------------------------------------------

    target_columns = {}

    for metric, aliases in TARGETS.items():

        column = find_column(
            df.columns,
            aliases
        )

        if column is not None:
            target_columns[metric] = column

    print("\nDetected target columns:")

    for metric in TARGETS:
        print(
            f"  {metric}: "
            f"{target_columns.get(metric)}"
        )

    # ---------------------------------------------------------
    # PARSE TEXT
    # ---------------------------------------------------------

    records = []
    failures = []

    for _, row in df.iterrows():

        company_id = str(
            row[company_col]
        ).strip()

        if (
            not company_id
            or company_id.lower() == "nan"
        ):
            continue

        for metric in TARGETS:

            column = target_columns.get(metric)

            if column is None:

                failures.append({
                    "company_id": company_id,
                    "metric_type": metric,
                    "source_column": "",
                    "raw_text": "",
                    "reason": "target column not found",
                })

                continue

            raw_value = row[column]

            if pd.isna(raw_value):

                failures.append({
                    "company_id": company_id,
                    "metric_type": metric,
                    "source_column": column,
                    "raw_text": "",
                    "reason": "blank value",
                })

                continue

            text = str(
                raw_value
            ).strip()

            matches = PATTERN.findall(
                text
            )

            if not matches:

                failures.append({
                    "company_id": company_id,
                    "metric_type": metric,
                    "source_column": column,
                    "raw_text": text,
                    "reason": "regex pattern did not match",
                })

                continue

            for period, value in matches:

                records.append({
                    "company_id": company_id,
                    "metric_type": metric,
                    "period_years": int(period),
                    "value_pct": float(value),
                })

    # ---------------------------------------------------------
    # CREATE OUTPUT DATAFRAMES
    # ---------------------------------------------------------

    parsed = pd.DataFrame(
        records,
        columns=[
            "company_id",
            "metric_type",
            "period_years",
            "value_pct",
        ]
    )

    failures_df = pd.DataFrame(
        failures,
        columns=[
            "company_id",
            "metric_type",
            "source_column",
            "raw_text",
            "reason",
        ]
    )

    # ---------------------------------------------------------
    # SAVE PARSED OUTPUT
    # ---------------------------------------------------------

    parsed.to_csv(
        PARSED_PATH,
        index=False
    )

    failures_df.to_csv(
        FAILURES_PATH,
        index=False
    )

    # ---------------------------------------------------------
    # CROSS-VALIDATE AGAINST RATIO ENGINE
    # ---------------------------------------------------------

    validation_records = []

    conn = sqlite3.connect(
        DB_PATH
    )

    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        conn
    )

    conn.close()

    if not ratios.empty:

        ratios["company_id"] = (
            ratios["company_id"]
            .astype(str)
            .str.strip()
        )

        ratios["year"] = pd.to_numeric(
            ratios["year"],
            errors="coerce"
        )

        ratios = ratios.sort_values(
            [
                "company_id",
                "year",
            ]
        )

        ratio_map = {
            "compounded_sales_growth":
                "revenue_cagr_5yr",

            "compounded_profit_growth":
                "pat_cagr_5yr",

            "roe":
                "return_on_equity_pct",
        }

        latest_ratios = (
            ratios
            .groupby(
                "company_id",
                as_index=False
            )
            .tail(1)
        )

        for metric, ratio_column in ratio_map.items():

            if ratio_column not in latest_ratios.columns:
                continue

            latest_ratios[ratio_column] = (
                pd.to_numeric(
                    latest_ratios[ratio_column],
                    errors="coerce"
                )
            )

            ratio_lookup = (
                latest_ratios
                .set_index("company_id")[
                    ratio_column
                ]
                .to_dict()
            )

            metric_rows = parsed[
                parsed["metric_type"] == metric
            ]

            for _, parsed_row in metric_rows.iterrows():

                if (
                    parsed_row["period_years"]
                    != 5
                ):
                    continue

                company_id = (
                    parsed_row["company_id"]
                )

                computed = ratio_lookup.get(
                    company_id
                )

                if pd.isna(computed):
                    continue

                if computed == 0:
                    continue

                parsed_value = (
                    parsed_row["value_pct"]
                )

                divergence = (
                    abs(
                        parsed_value
                        - computed
                    )
                    / abs(computed)
                    * 100
                )

                validation_records.append({
                    "company_id": company_id,
                    "metric_type": metric,
                    "period_years": 5,
                    "parsed_value_pct": parsed_value,
                    "ratio_engine_value_pct": computed,
                    "divergence_pct": divergence,
                    "manual_review": divergence > 5,
                })

    validation_df = pd.DataFrame(
        validation_records
    )

    validation_df.to_csv(
        VALIDATION_PATH,
        index=False
    )

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("PARSER OUTPUT")
    print("=" * 70)

    print(
        f"Parsed records : {len(parsed)}"
    )

    print(
        f"Parse failures : {len(failures_df)}"
    )

    if not validation_df.empty:

        manual_reviews = int(
            validation_df[
                "manual_review"
            ].sum()
        )

        print(
            f"Manual reviews : {manual_reviews}"
        )

    else:

        print(
            "Manual reviews : 0"
        )

    print("\nMetric counts:")

    if not parsed.empty:

        print(
            parsed[
                "metric_type"
            ]
            .value_counts()
            .to_string()
        )

    print("\nOutput files:")

    print(
        f"  {PARSED_PATH}"
    )

    print(
        f"  {FAILURES_PATH}"
    )

    print(
        f"  {VALIDATION_PATH}"
    )

    print("\nPARSER COMPLETE")


if __name__ == "__main__":
    main()