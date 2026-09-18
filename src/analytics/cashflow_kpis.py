from typing import Optional


def _to_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ============================================================
# DAY 11 — CASH FLOW KPIs
# ============================================================

def free_cash_flow(
    operating_activity,
    investing_activity,
) -> Optional[float]:

    operating_activity = _to_float(operating_activity)
    investing_activity = _to_float(investing_activity)

    if operating_activity is None or investing_activity is None:
        return None

    return operating_activity + investing_activity


def cfo_pat_ratio(
    cfo,
    pat,
) -> Optional[float]:

    cfo = _to_float(cfo)
    pat = _to_float(pat)

    if cfo is None or pat is None:
        return None

    if pat == 0:
        return None

    return cfo / pat


def classify_cfo_quality(ratio):

    if ratio is None:
        return None

    if ratio > 1:
        return "High Quality"

    if ratio >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def capex_intensity(
    investing_activity,
    sales,
) -> Optional[float]:

    investing_activity = _to_float(investing_activity)
    sales = _to_float(sales)

    if investing_activity is None or sales is None:
        return None

    if sales == 0:
        return None

    return abs(investing_activity) / sales * 100


def classify_capex_intensity(intensity):

    if intensity is None:
        return None

    if intensity < 3:
        return "Asset Light"

    if intensity <= 8:
        return "Moderate"

    return "Capital Intensive"


def fcf_conversion_rate(
    free_cash_flow_value,
    operating_profit,
) -> Optional[float]:

    free_cash_flow_value = _to_float(free_cash_flow_value)
    operating_profit = _to_float(operating_profit)

    if free_cash_flow_value is None or operating_profit is None:
        return None

    if operating_profit == 0:
        return None

    return free_cash_flow_value / operating_profit * 100


def sign(value):

    value = _to_float(value)

    if value is None:
        return None

    if value > 0:
        return "+"

    if value < 0:
        return "-"

    return "0"


def capital_allocation_pattern(
    cfo,
    cfi,
    cff,
    cfo_pat_ratio_value=None,
):

    pattern = (
        sign(cfo),
        sign(cfi),
        sign(cff),
    )

    if pattern == ("+", "-", "-"):

        if (
            cfo_pat_ratio_value is not None
            and cfo_pat_ratio_value > 1
        ):
            return "Shareholder Returns"

        return "Reinvestor"

    if pattern == ("+", "+", "-"):
        return "Liquidating Assets"

    if pattern == ("-", "+", "+"):
        return "Distress Signal"

    if pattern == ("-", "-", "+"):
        return "Growth Funded by Debt"

    if pattern == ("+", "+", "+"):
        return "Cash Accumulator"

    if pattern == ("-", "-", "-"):
        return "Pre-Revenue"

    if pattern == ("+", "-", "+"):
        return "Mixed"

    return "Mixed"


def calculate_cashflow_kpis(
    operating_activity,
    investing_activity,
    financing_activity,
    pat,
    sales,
    operating_profit,
):

    fcf = free_cash_flow(
        operating_activity,
        investing_activity,
    )

    ratio = cfo_pat_ratio(
        operating_activity,
        pat,
    )

    quality = classify_cfo_quality(
        ratio
    )

    intensity = capex_intensity(
        investing_activity,
        sales,
    )

    classification = classify_capex_intensity(
        intensity
    )

    conversion = fcf_conversion_rate(
        fcf,
        operating_profit,
    )

    pattern = capital_allocation_pattern(
        operating_activity,
        investing_activity,
        financing_activity,
        ratio,
    )

    return {
        # Original test-compatible key
        "free_cash_flow": fcf,

        # Day 12 database-compatible key
        "free_cash_flow_cr": fcf,

        "cfo_pat_ratio": ratio,
        "cfo_quality": quality,
        "capex_intensity_pct": intensity,
        "capex_classification": classification,
        "fcf_conversion_rate_pct": conversion,
        "cfo_sign": sign(operating_activity),
        "cfi_sign": sign(investing_activity),
        "cff_sign": sign(financing_activity),
        "capital_allocation_pattern": pattern,
    }