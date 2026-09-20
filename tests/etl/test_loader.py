import pandas as pd
import pytest

from src.etl.loader import prepare_dataset
from src.etl.validator import (
    find_excel_file,
    normalize_columns,
    normalize_company_id,
)


def test_normalize_company_id_basic():
    assert normalize_company_id("RELIANCE") == "RELIANCE"


def test_normalize_company_id_lowercase():
    assert normalize_company_id("reliance") == "RELIANCE"


def test_normalize_company_id_ns_suffix():
    assert normalize_company_id("RELIANCE.NS") == "RELIANCE"


def test_normalize_company_id_nse_suffix():
    assert normalize_company_id("RELIANCE-NSE") == "RELIANCE"


def test_normalize_company_id_known_alias():
    assert normalize_company_id("AGTL") == "ATGL"


def test_normalize_company_id_bajaj_auto():
    assert normalize_company_id("BAJAJ-AUTO") == "BAJAJAUTO"


def test_normalize_company_id_empty():
    assert normalize_company_id("") is None


def test_normalize_columns():
    df = pd.DataFrame(
        columns=[
            " Company Name ",
            "Operating Profit",
            "Debt-to-Equity",
            "Research & Development",
        ]
    )

    result = normalize_columns(df)

    assert list(result.columns) == [
        "company_name",
        "operating_profit",
        "debt_to_equity",
        "research_and_development",
    ]


def test_prepare_dataset_normalizes_ids_and_year():
    df = pd.DataFrame(
        {
            "company_id": ["reliance.ns", "AGTL"],
            "year": ["Mar 2024", "FY 2023"],
        }
    )

    result = prepare_dataset("test", df)

    assert result["company_id"].tolist() == ["RELIANCE", "ATGL"]
    assert result["year"].tolist() == [2024, 2023]
    assert "_raw_year" in result.columns


def test_find_excel_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_excel_file(tmp_path, "does_not_exist")
