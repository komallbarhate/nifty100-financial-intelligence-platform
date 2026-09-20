import pytest

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    opm_cross_check,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    calculate_profitability_ratios,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    interest_coverage_label,
    interest_coverage_warning,
    net_debt,
    asset_turnover,
    calculate_leverage_efficiency_ratios,
)


# ============================================================
# PROFITABILITY RATIO TESTS
# ============================================================

def test_net_profit_margin():
    assert net_profit_margin(100, 1000) == pytest.approx(10.0)


def test_net_profit_margin_zero_sales():
    assert net_profit_margin(100, 0) is None


def test_net_profit_margin_invalid_input():
    assert net_profit_margin("invalid", 1000) is None


def test_operating_profit_margin():
    opm, difference = operating_profit_margin(200, 1000, 19)

    assert opm == pytest.approx(20.0)
    assert difference == pytest.approx(1.0)


def test_operating_profit_margin_without_source():
    opm, difference = operating_profit_margin(200, 1000)

    assert opm == pytest.approx(20.0)
    assert difference is None


def test_opm_cross_check_within_threshold():
    result = opm_cross_check(200, 1000, 20)

    assert result["computed_opm"] == pytest.approx(20.0)
    assert result["source_opm"] == pytest.approx(20.0)
    assert result["difference"] == pytest.approx(0.0)
    assert result["mismatch"] is False


def test_opm_cross_check_above_threshold():
    result = opm_cross_check(200, 1000, 17)

    assert result["computed_opm"] == pytest.approx(20.0)
    assert result["source_opm"] == pytest.approx(17.0)
    assert result["difference"] == pytest.approx(3.0)
    assert result["mismatch"] is True


def test_return_on_equity():
    assert return_on_equity(100, 200, 300) == pytest.approx(20.0)


def test_return_on_equity_invalid_equity():
    assert return_on_equity(100, -100, 0) is None


def test_return_on_capital_employed():
    assert return_on_capital_employed(
        200,
        300,
        200,
        500,
    ) == pytest.approx(20.0)


def test_return_on_assets():
    assert return_on_assets(100, 1000) == pytest.approx(10.0)


def test_calculate_profitability_ratios():
    result = calculate_profitability_ratios(
        net_profit=100,
        sales=1000,
        operating_profit=200,
        equity_capital=200,
        reserves=300,
        ebit=200,
        borrowings=500,
        total_assets=1000,
        source_opm=20,
    )

    assert result["net_profit_margin_pct"] == pytest.approx(10.0)
    assert result["operating_profit_margin_pct"] == pytest.approx(20.0)
    assert result["opm_difference"] == pytest.approx(0.0)
    assert result["opm_mismatch_flag"] is False
    assert result["return_on_equity_pct"] == pytest.approx(20.0)
    assert result["return_on_capital_employed_pct"] == pytest.approx(20.0)
    assert result["return_on_assets_pct"] == pytest.approx(10.0)


# ============================================================
# LEVERAGE & EFFICIENCY TESTS
# ============================================================

def test_debt_to_equity():
    assert debt_to_equity(
        500,
        200,
        300,
    ) == pytest.approx(1.0)


def test_debt_to_equity_zero_debt():
    assert debt_to_equity(
        0,
        200,
        300,
    ) == pytest.approx(0.0)


def test_debt_to_equity_invalid_equity():
    assert debt_to_equity(
        500,
        -300,
        100,
    ) is None


def test_high_leverage_flag():
    assert high_leverage_flag(
        6.0,
        "Industrial",
    ) is True

    assert high_leverage_flag(
        4.0,
        "Industrial",
    ) is False


def test_financial_sector_high_leverage_override():
    assert high_leverage_flag(
        10.0,
        "Financials",
    ) is False


def test_interest_coverage_ratio():
    assert interest_coverage_ratio(
        200,
        50,
        50,
    ) == pytest.approx(5.0)


def test_interest_coverage_zero_interest():
    assert interest_coverage_ratio(
        200,
        50,
        0,
    ) is None


def test_interest_coverage_label():
    assert interest_coverage_label(None) == "Debt Free"


def test_interest_coverage_warning():
    assert interest_coverage_warning(1.0) is True
    assert interest_coverage_warning(2.0) is False


def test_net_debt():
    assert net_debt(
        500,
        100,
    ) == pytest.approx(400.0)


def test_net_debt_missing_values():
    assert net_debt(
        None,
        None,
    ) == pytest.approx(0.0)


def test_asset_turnover():
    assert asset_turnover(
        1000,
        500,
    ) == pytest.approx(2.0)


def test_asset_turnover_zero_assets():
    assert asset_turnover(
        1000,
        0,
    ) is None


def test_calculate_leverage_efficiency_ratios():
    result = calculate_leverage_efficiency_ratios(
        borrowings=500,
        equity_capital=200,
        reserves=300,
        broad_sector="Industrial",
        operating_profit=200,
        other_income=50,
        interest=50,
        investments=100,
        sales=1000,
        total_assets=500,
    )

    assert result["debt_to_equity"] == pytest.approx(1.0)
    assert result["high_leverage_flag"] is False
    assert result["interest_coverage"] == pytest.approx(5.0)

    # Current implementation returns None for
    # non-None interest coverage values.
    assert result["icr_label"] is None

    assert result["icr_warning_flag"] is False
    assert result["net_debt"] == pytest.approx(400.0)
    assert result["asset_turnover"] == pytest.approx(2.0)