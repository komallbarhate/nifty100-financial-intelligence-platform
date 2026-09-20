import pytest

from src.etl.validator import normalize_year


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2024", 2024),
        ("2023", 2023),
        ("2022", 2022),
        ("2021", 2021),
        ("2020", 2020),
        ("FY 2024", 2024),
        ("Mar 2024", 2024),
        ("Sep 2024", 2024),
        ("March 2023", 2023),
        ("December 2022", 2022),
        ("2024-25", 2024),
        ("FY 2024-25", 2024),
        (2024, 2024),
        (2023.0, 2023),
        (2000, 2000),
        (" 2024 ", 2024),
        ("Financial Year 2024", 2024),
        (None, None),
        ("", None),
        ("not a year", None),
    ],
)
def test_normalize_year(value, expected):
    assert normalize_year(value) == expected


def test_normalize_year_nan():
    assert normalize_year(float("nan")) is None


def test_normalize_year_out_of_range():
    assert normalize_year("1899") is None
    assert normalize_year("2101") is None


def test_normalize_year_invalid_numeric():
    assert normalize_year("999") is None


def test_normalize_year_none():
    assert normalize_year(None) is None