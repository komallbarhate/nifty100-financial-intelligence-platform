import pytest

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    opm_cross_check,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    calculate_profitability_ratios,
)


def test_net_profit_margin_normal():
    result = net_profit_margin(20, 100)

    assert result == pytest.approx(20.0)


def test_net_profit_margin_zero_sales():
    result = net_profit_margin(20, 0)

    assert result is None


def test_operating_profit_margin_normal():
    result, difference = operating_profit_margin(
        30,
        100,
        30,
    )

    assert result == pytest.approx(30.0)
    assert difference == pytest.approx(0.0)


def test_opm_cross_check_mismatch():
    result = opm_cross_check(
        30,
        100,
        25,
    )

    assert result["computed_opm"] == pytest.approx(30.0)
    assert result["difference"] == pytest.approx(5.0)
    assert result["mismatch"] is True


def test_opm_cross_check_within_threshold():
    result = opm_cross_check(
        30,
        100,
        29.5,
    )

    assert result["computed_opm"] == pytest.approx(30.0)
    assert result["difference"] == pytest.approx(0.5)
    assert result["mismatch"] is False


def test_roe_normal():
    result = return_on_equity(
        20,
        50,
        50,
    )

    assert result == pytest.approx(20.0)


def test_roe_negative_equity():
    result = return_on_equity(
        20,
        40,
        -50,
    )

    assert result is None


def test_roce_normal():
    result = return_on_capital_employed(
        30,
        50,
        50,
        50,
    )

    assert result == pytest.approx(20.0)


def test_roa_zero_assets():
    result = return_on_assets(
        20,
        0,
    )

    assert result is None


def test_combined_profitability_ratios():
    result = calculate_profitability_ratios(
        net_profit=20,
        sales=100,
        operating_profit=30,
        equity_capital=50,
        reserves=50,
        ebit=30,
        borrowings=50,
        total_assets=150,
        source_opm=30,
    )

    assert result["net_profit_margin_pct"] == pytest.approx(20.0)
    assert result["operating_profit_margin_pct"] == pytest.approx(30.0)
    assert result["return_on_equity_pct"] == pytest.approx(20.0)
    assert result["return_on_capital_employed_pct"] == pytest.approx(20.0)
    assert result["return_on_assets_pct"] == pytest.approx(
        13.3333333333
    )
    assert result["opm_mismatch_flag"] is False