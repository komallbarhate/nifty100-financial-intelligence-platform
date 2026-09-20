import pytest

from src.analytics.ratios import (
    asset_turnover,
    calculate_leverage_efficiency_ratios,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_label,
    interest_coverage_ratio,
    interest_coverage_warning,
    net_debt,
)


def test_debt_to_equity_normal():
    result = debt_to_equity(
        borrowings=50,
        equity_capital=50,
        reserves=50,
    )

    assert result == pytest.approx(0.5)


def test_debt_to_equity_debt_free_returns_zero():
    result = debt_to_equity(
        borrowings=0,
        equity_capital=100,
        reserves=50,
    )

    assert result == 0.0


def test_debt_to_equity_negative_equity_returns_none():
    result = debt_to_equity(
        borrowings=50,
        equity_capital=40,
        reserves=-50,
    )

    assert result is None


def test_high_debt_equity_flag():
    result = high_leverage_flag(
        debt_equity=6.0,
        broad_sector="Industrials",
    )

    assert result is True


def test_financials_high_debt_equity_not_flagged():
    result = high_leverage_flag(
        debt_equity=8.0,
        broad_sector="Financials",
    )

    assert result is False


def test_interest_coverage_normal():
    result = interest_coverage_ratio(
        operating_profit=100,
        other_income=20,
        interest=20,
    )

    assert result == pytest.approx(6.0)


def test_interest_zero_returns_none():
    result = interest_coverage_ratio(
        operating_profit=100,
        other_income=20,
        interest=0,
    )

    assert result is None


def test_icr_none_gets_debt_free_label():
    result = interest_coverage_label(None)

    assert result == "Debt Free"


def test_icr_below_threshold_warning():
    result = interest_coverage_warning(1.2)

    assert result is True


def test_net_debt():
    result = net_debt(
        borrowings=100,
        investments=30,
    )

    assert result == pytest.approx(70.0)


def test_asset_turnover_normal():
    result = asset_turnover(
        sales=200,
        total_assets=100,
    )

    assert result == pytest.approx(2.0)


def test_asset_turnover_zero_assets():
    result = asset_turnover(
        sales=200,
        total_assets=0,
    )

    assert result is None


def test_combined_leverage_efficiency():
    result = calculate_leverage_efficiency_ratios(
        borrowings=50,
        equity_capital=50,
        reserves=50,
        operating_profit=100,
        other_income=20,
        interest=20,
        investments=10,
        sales=200,
        total_assets=100,
        broad_sector="Industrials",
    )

    assert result["debt_to_equity"] == pytest.approx(0.5)
    assert result["high_leverage_flag"] is False
    assert result["interest_coverage"] == pytest.approx(6.0)
    assert result["icr_label"] is None
    assert result["icr_warning_flag"] is False
    assert result["net_debt"] == pytest.approx(40.0)
    assert result["asset_turnover"] == pytest.approx(2.0)
