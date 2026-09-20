import pytest

from src.analytics.cagr import (
    BOTH_NEGATIVE,
    DECLINE_TO_LOSS,
    INSUFFICIENT,
    TURNAROUND,
    ZERO_BASE,
    calculate_all_cagr_windows,
    calculate_cagr,
    calculate_company_growth_metrics,
    calculate_window_cagr,
)


def test_normal_cagr():
    value, flag = calculate_cagr(
        100,
        121,
        2,
    )

    assert value == pytest.approx(10.0)
    assert flag is None


def test_decline_to_loss():
    value, flag = calculate_cagr(
        100,
        -20,
        5,
    )

    assert value is None
    assert flag == DECLINE_TO_LOSS


def test_turnaround():
    value, flag = calculate_cagr(
        -100,
        200,
        5,
    )

    assert value is None
    assert flag == TURNAROUND


def test_both_negative():
    value, flag = calculate_cagr(
        -100,
        -200,
        5,
    )

    assert value is None
    assert flag == BOTH_NEGATIVE


def test_zero_base():
    value, flag = calculate_cagr(
        0,
        100,
        5,
    )

    assert value is None
    assert flag == ZERO_BASE


def test_insufficient_years():
    values = {
        2022: 100,
        2023: 110,
        2024: 120,
    }

    value, flag = calculate_window_cagr(
        values,
        2024,
        5,
    )

    assert value is None
    assert flag == INSUFFICIENT


def test_three_year_cagr():
    values = {
        2021: 100,
        2022: 110,
        2023: 121,
        2024: 133.1,
    }

    value, flag = calculate_window_cagr(
        values,
        2024,
        3,
    )

    assert value == pytest.approx(10.0)
    assert flag is None


def test_five_year_cagr():
    values = {
        2019: 100,
        2020: 110,
        2021: 121,
        2022: 133.1,
        2023: 146.41,
        2024: 161.051,
    }

    value, flag = calculate_window_cagr(
        values,
        2024,
        5,
    )

    assert value == pytest.approx(10.0)
    assert flag is None


def test_all_cagr_windows():
    values = {
        2014: 100,
        2019: 150,
        2021: 170,
        2022: 180,
        2023: 190,
        2024: 200,
    }

    result = calculate_all_cagr_windows(
        values,
        2024,
    )

    assert "cagr_3yr" in result
    assert "cagr_5yr" in result
    assert "cagr_10yr" in result

    assert result["cagr_3yr"] is not None
    assert result["cagr_5yr"] is not None
    assert result["cagr_10yr"] is not None


def test_company_growth_metrics():
    revenue = {
        2014: 100,
        2019: 150,
        2021: 170,
        2022: 180,
        2023: 190,
        2024: 200,
    }

    pat = {
        2014: 20,
        2019: 30,
        2021: 35,
        2022: 36,
        2023: 38,
        2024: 40,
    }

    eps = {
        2014: 10,
        2019: 15,
        2021: 17,
        2022: 18,
        2023: 19,
        2024: 20,
    }

    result = calculate_company_growth_metrics(
        revenue,
        pat,
        eps,
        2024,
    )

    assert result["revenue_cagr_5yr"] is not None
    assert result["pat_cagr_5yr"] is not None
    assert result["eps_cagr_5yr"] is not None

    assert "revenue_cagr_5yr_flag" in result
    assert "pat_cagr_5yr_flag" in result
    assert "eps_cagr_5yr_flag" in result


def test_positive_to_zero_is_decline_to_loss():
    value, flag = calculate_cagr(
        100,
        0,
        5,
    )

    assert value is None
    assert flag == DECLINE_TO_LOSS
