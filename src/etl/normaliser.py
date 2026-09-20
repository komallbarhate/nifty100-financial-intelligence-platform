import re

import pandas as pd

# ============================================================
# YEAR NORMALISATION
# ============================================================


def normalize_year(value):
    """Normalize year."""
    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return int(value.year)

    value = str(value).strip()

    if not value:
        return None

    match = re.search(r"\b(19|20)\d{2}\b", value)

    if match:
        return int(match.group(0))

    month_year = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)" r"[a-z]*[-\s/]?(\d{2})$",
        value,
        re.IGNORECASE,
    )

    if month_year:
        short_year = int(month_year.group(2))

        if short_year >= 50:
            return 1900 + short_year
        else:
            return 2000 + short_year

    try:
        number = float(value)

        if 1900 <= number <= 2100:
            return int(number)

    except (ValueError, TypeError):
        pass

    return None


# ============================================================
# TICKER NORMALISATION
# ============================================================


def normalize_ticker(value):
    """Normalize ticker."""
    if pd.isna(value):
        return None

    ticker = str(value).strip().upper()

    if not ticker:
        return None

    # Remove exchange suffixes
    ticker = re.sub(r"\.(NS|BO)$", "", ticker)

    ticker = re.sub(r"[-_](BSE|NSE)$", "", ticker)

    # Known source-data alias
    # AGTL in cashflow data refers to ATGL,
    # which is the company ID present in companies.xlsx.
    if ticker == "AGTL":
        ticker = "ATGL"

    # Remove unwanted characters
    ticker = re.sub(r"[^A-Z0-9&]", "", ticker)

    return ticker


# ============================================================
# COMPANY NAME NORMALISATION
# ============================================================


def normalize_company_name(value):
    """Normalize company name."""
    if pd.isna(value):
        return None

    name = str(value).strip()

    name = re.sub(r"\s+", " ", name)

    return name


# ============================================================
# DATAFRAME NORMALISATION
# ============================================================


def normalize_dataframe(df):
    """Normalize dataframe."""
    df = df.copy()

    for column in df.columns:

        column_lower = str(column).lower().strip()

        if column_lower in [
            "year",
            "fy",
            "financial_year",
            "fiscal_year",
        ]:
            df[column] = df[column].apply(normalize_year)

        elif column_lower in [
            "ticker",
            "symbol",
            "stock_ticker",
            "company_id",
        ]:
            df[column] = df[column].apply(normalize_ticker)

        elif column_lower in [
            "company_name",
            "company",
            "name",
        ]:
            df[column] = df[column].apply(normalize_company_name)

    return df
