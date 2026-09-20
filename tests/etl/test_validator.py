import pandas as pd

from src.etl.validator import (
    dq01_primary_key,
    dq02_company_year_uniqueness,
    dq03_foreign_keys,
    dq05_opm_crosscheck,
    dq06_positive_sales,
    dq07_net_cash,
    dq09_tax_rate,
    dq10_dividend_cap,
    dq11_url_validation,
    dq12_eps_sign,
    dq13_bse_balance,
    dq14_coverage,
    dq15_missing_values,
    dq16_year_coverage,
)


# ============================================================
# DQ-01 PRIMARY KEY
# ============================================================

def test_dq01_detects_duplicate_company_id():
    df = pd.DataFrame(
        {
            "id": ["ABC", "ABC", "XYZ"],
        }
    )

    failures = []

    dq01_primary_key(
        "companies",
        df,
        failures,
    )

    assert len(failures) == 2
    assert all(item["rule_id"] == "DQ-01" for item in failures)
    assert all(item["severity"] == "CRITICAL" for item in failures)


def test_dq01_no_failure_for_unique_ids():
    df = pd.DataFrame(
        {
            "id": ["ABC", "XYZ"],
        }
    )

    failures = []

    dq01_primary_key(
        "companies",
        df,
        failures,
    )

    assert failures == []


# ============================================================
# DQ-02 COMPANY-YEAR UNIQUENESS
# ============================================================

def test_dq02_detects_duplicate_business_key():
    df = pd.DataFrame(
        {
            "company_id": ["ABC", "ABC"],
            "year": [2024, 2024],
            "_raw_year": ["Mar 2024", "Mar 2024"],
        }
    )

    failures = []

    dq02_company_year_uniqueness(
        "financial_ratios",
        df,
        failures,
    )

    assert len(failures) == 2
    assert all(item["rule_id"] == "DQ-02" for item in failures)
    assert all(item["severity"] == "CRITICAL" for item in failures)


def test_dq02_allows_different_years():
    df = pd.DataFrame(
        {
            "company_id": ["ABC", "ABC"],
            "year": [2024, 2023],
            "_raw_year": ["Mar 2024", "Mar 2023"],
        }
    )

    failures = []

    dq02_company_year_uniqueness(
        "financial_ratios",
        df,
        failures,
    )

    assert failures == []


# ============================================================
# DQ-03 FOREIGN KEYS
# ============================================================

def test_dq03_detects_missing_company_id():
    datasets = {
        "companies": pd.DataFrame(
            {
                "id": ["ABC", "XYZ"],
            }
        ),
        "financial_ratios": pd.DataFrame(
            {
                "company_id": ["ABC", "MISSING"],
            }
        ),
    }

    failures = []

    dq03_foreign_keys(
        datasets,
        failures,
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-03"
    assert failures[0]["severity"] == "CRITICAL"
    assert "MISSING" in failures[0]["message"]


def test_dq03_accepts_known_company():
    datasets = {
        "companies": pd.DataFrame(
            {
                "id": ["ABC", "XYZ"],
            }
        ),
        "financial_ratios": pd.DataFrame(
            {
                "company_id": ["ABC", "XYZ"],
            }
        ),
    }

    failures = []

    dq03_foreign_keys(
        datasets,
        failures,
    )

    assert failures == []


# ============================================================
# DQ-05 OPM CROSS-CHECK
# ============================================================

def test_dq05_detects_opm_mismatch():
    datasets = {
        "profitandloss": pd.DataFrame(
            {
                "company_id": ["ABC"],
                "sales": [1000],
                "operating_profit": [200],
                "opm": [10],
            }
        )
    }

    failures = []

    dq05_opm_crosscheck(
        datasets,
        failures,
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-05"
    assert failures[0]["severity"] == "WARNING"


def test_dq05_accepts_correct_opm():
    datasets = {
        "profitandloss": pd.DataFrame(
            {
                "company_id": ["ABC"],
                "sales": [1000],
                "operating_profit": [200],
                "opm": [20],
            }
        )
    }

    failures = []

    dq05_opm_crosscheck(
        datasets,
        failures,
    )

    assert failures == []


# ============================================================
# DQ-06 POSITIVE SALES
# ============================================================

def test_dq06_detects_negative_sales():
    datasets = {
        "profitandloss": pd.DataFrame(
            {
                "company_id": ["ABC"],
                "year": [2024],
                "sales": [-100],
            }
        )
    }

    failures = []

    dq06_positive_sales(
        datasets,
        failures,
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-06"
    assert failures[0]["severity"] == "CRITICAL"


def test_dq06_accepts_positive_sales():
    datasets = {
        "profitandloss": pd.DataFrame(
            {
                "company_id": ["ABC"],
                "year": [2024],
                "sales": [100],
            }
        )
    }

    failures = []

    dq06_positive_sales(
        datasets,
        failures,
    )

    assert failures == []


# ============================================================
# DQ-07 NET CASH
# ============================================================

def test_dq07_is_currently_noop():
    failures = []

    dq07_net_cash(
        {},
        failures,
    )

    assert failures == []


# ============================================================
# DQ-09 TAX RATE
# ============================================================

def test_dq09_detects_invalid_tax_rate():
    datasets = {
        "profitandloss": pd.DataFrame(
            {
                "tax_rate": [150],
            }
        )
    }

    failures = []

    dq09_tax_rate(
        datasets,
        failures,
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-09"
    assert failures[0]["severity"] == "WARNING"


def test_dq09_accepts_valid_tax_rate():
    datasets = {
        "profitandloss": pd.DataFrame(
            {
                "tax_rate": [25],
            }
        )
    }

    failures = []

    dq09_tax_rate(
        datasets,
        failures,
    )

    assert failures == []


# ============================================================
# DQ-10 DIVIDEND CAP
# ============================================================

def test_dq10_is_currently_noop():
    failures = []

    dq10_dividend_cap(
        {},
        failures,
    )

    assert failures == []


# ============================================================
# DQ-11 URL VALIDATION
# ============================================================

def test_dq11_detects_invalid_url():
    datasets = {
        "companies": pd.DataFrame(
            {
                "website": ["example.com"],
            }
        )
    }

    failures = []

    dq11_url_validation(
        datasets,
        failures,
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-11"
    assert failures[0]["severity"] == "WARNING"


def test_dq11_accepts_valid_url():
    datasets = {
        "companies": pd.DataFrame(
            {
                "website": ["https://example.com"],
            }
        )
    }

    failures = []

    dq11_url_validation(
        datasets,
        failures,
    )

    assert failures == []


# ============================================================
# DQ-12 TO DQ-16 CURRENT NO-OP RULES
# ============================================================

def test_dq12_is_currently_noop():
    failures = []

    dq12_eps_sign(
        {},
        failures,
    )

    assert failures == []


def test_dq13_is_currently_noop():
    failures = []

    dq13_bse_balance(
        {},
        failures,
    )

    assert failures == []


def test_dq14_is_currently_noop():
    failures = []

    dq14_coverage(
        {},
        failures,
    )

    assert failures == []


def test_dq15_is_currently_noop():
    failures = []

    dq15_missing_values(
        {},
        failures,
    )

    assert failures == []


def test_dq16_is_currently_noop():
    failures = []

    dq16_year_coverage(
        {},
        failures,
    )

    assert failures == []