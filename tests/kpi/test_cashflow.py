import pytest

from src.analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_pat_ratio,
    classify_cfo_quality,
    capex_intensity,
    classify_capex_intensity,
    fcf_conversion_rate,
    capital_allocation_pattern,
    calculate_cashflow_kpis,
)


def test_free_cash_flow():
    result = free_cash_flow(
        operating_activity=100,
        investing_activity=-40,
    )

    assert result == pytest.approx(60.0)


def test_negative_free_cash_flow_allowed():
    result = free_cash_flow(
        operating_activity=50,
        investing_activity=-100,
    )

    assert result == pytest.approx(-50.0)


def test_cfo_pat_ratio_zero_pat():
    result = cfo_pat_ratio(
        cfo=100,
        pat=0,
    )

    assert result is None


def test_cfo_quality_high():
    result = classify_cfo_quality(1.5)

    assert result == "High Quality"


def test_cfo_quality_moderate():
    result = classify_cfo_quality(0.75)

    assert result == "Moderate"


def test_cfo_quality_accrual_risk():
    result = classify_cfo_quality(0.25)

    assert result == "Accrual Risk"


def test_capex_intensity():
    result = capex_intensity(
        investing_activity=-20,
        sales=1000,
    )

    assert result == pytest.approx(2.0)


def test_capex_asset_light():
    result = classify_capex_intensity(2.5)

    assert result == "Asset Light"


def test_capex_moderate():
    result = classify_capex_intensity(5.0)

    assert result == "Moderate"


def test_capex_capital_intensive():
    result = classify_capex_intensity(10.0)

    assert result == "Capital Intensive"


def test_fcf_conversion_zero_operating_profit():
    result = fcf_conversion_rate(
        free_cash_flow_value=100,
        operating_profit=0,
    )

    assert result is None


def test_capital_allocation_reinvestor():
    result = capital_allocation_pattern(
        cfo=100,
        cfi=-50,
        cff=-20,
        cfo_pat_ratio_value=0.8,
    )

    assert result == "Reinvestor"


def test_capital_allocation_shareholder_returns():
    result = capital_allocation_pattern(
        cfo=100,
        cfi=-50,
        cff=-20,
        cfo_pat_ratio_value=1.5,
    )

    assert result == "Shareholder Returns"


def test_capital_allocation_liquidating_assets():
    result = capital_allocation_pattern(
        cfo=100,
        cfi=50,
        cff=-20,
    )

    assert result == "Liquidating Assets"


def test_capital_allocation_distress_signal():
    result = capital_allocation_pattern(
        cfo=-100,
        cfi=50,
        cff=20,
    )

    assert result == "Distress Signal"


def test_capital_allocation_growth_debt():
    result = capital_allocation_pattern(
        cfo=-100,
        cfi=-50,
        cff=100,
    )

    assert result == "Growth Funded by Debt"


def test_capital_allocation_cash_accumulator():
    result = capital_allocation_pattern(
        cfo=100,
        cfi=50,
        cff=20,
    )

    assert result == "Cash Accumulator"


def test_capital_allocation_pre_revenue():
    result = capital_allocation_pattern(
        cfo=-100,
        cfi=-50,
        cff=-20,
    )

    assert result == "Pre-Revenue"


def test_capital_allocation_mixed():
    result = capital_allocation_pattern(
        cfo=100,
        cfi=-50,
        cff=20,
    )

    assert result == "Mixed"


def test_combined_cashflow_kpis():
    result = calculate_cashflow_kpis(
        operating_activity=100,
        investing_activity=-40,
        financing_activity=-20,
        pat=80,
        sales=1000,
        operating_profit=200,
    )

    assert result["free_cash_flow"] == pytest.approx(60.0)
    assert result["cfo_pat_ratio"] == pytest.approx(1.25)
    assert result["cfo_quality"] == "High Quality"
    assert result["capex_intensity_pct"] == pytest.approx(4.0)
    assert result["capex_classification"] == "Moderate"
    assert result["fcf_conversion_rate_pct"] == pytest.approx(30.0)
    assert result["capital_allocation_pattern"] == "Shareholder Returns"