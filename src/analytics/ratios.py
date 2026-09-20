

def _to_float(value):
    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    return value


# ============================================================
# DAY 08 — PROFITABILITY RATIOS
# ============================================================


def net_profit_margin(
    net_profit,
    sales,
) -> float | None:
    """Process net profit margin."""
    net_profit = _to_float(net_profit)
    sales = _to_float(sales)

    if net_profit is None or sales is None:
        return None

    if sales <= 0:
        return None

    return (net_profit / sales) * 100


def operating_profit_margin(
    operating_profit,
    sales,
    source_opm=None,
):
    """Process operating profit margin."""
    operating_profit = _to_float(operating_profit)
    sales = _to_float(sales)
    source_opm = _to_float(source_opm)

    if operating_profit is None or sales is None or sales <= 0:
        return None, None

    computed_opm = (operating_profit / sales) * 100

    difference = None

    if source_opm is not None:
        difference = abs(computed_opm - source_opm)

    return computed_opm, difference


def opm_cross_check(
    operating_profit,
    sales,
    source_opm,
    threshold=1.0,
):
    """Process opm cross check."""
    computed, difference = operating_profit_margin(
        operating_profit,
        sales,
        source_opm,
    )

    mismatch = difference is not None and difference > threshold

    return {
        "computed_opm": computed,
        "source_opm": _to_float(source_opm),
        "difference": difference,
        "mismatch": mismatch,
    }


def return_on_equity(
    net_profit,
    equity_capital,
    reserves,
) -> float | None:
    """Process return on equity."""
    net_profit = _to_float(net_profit)
    equity_capital = _to_float(equity_capital)
    reserves = _to_float(reserves)

    if net_profit is None or equity_capital is None or reserves is None:
        return None

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return (net_profit / equity) * 100


def return_on_capital_employed(
    ebit,
    equity_capital,
    reserves,
    borrowings,
) -> float | None:
    """Process return on capital employed."""
    ebit = _to_float(ebit)
    equity_capital = _to_float(equity_capital)
    reserves = _to_float(reserves)
    borrowings = _to_float(borrowings)

    if ebit is None or equity_capital is None or reserves is None or borrowings is None:
        return None

    capital_employed = equity_capital + reserves + borrowings

    if capital_employed <= 0:
        return None

    return (ebit / capital_employed) * 100


def return_on_assets(
    net_profit,
    total_assets,
) -> float | None:
    """Process return on assets."""
    net_profit = _to_float(net_profit)
    total_assets = _to_float(total_assets)

    if net_profit is None or total_assets is None:
        return None

    if total_assets <= 0:
        return None

    return (net_profit / total_assets) * 100


def calculate_profitability_ratios(
    net_profit,
    sales,
    operating_profit,
    equity_capital,
    reserves,
    ebit=None,
    borrowings=0,
    total_assets=None,
    source_opm=None,
):
    """Calculate profitability ratios."""
    npm = net_profit_margin(
        net_profit,
        sales,
    )

    opm, opm_difference = operating_profit_margin(
        operating_profit,
        sales,
        source_opm,
    )

    roe = return_on_equity(
        net_profit,
        equity_capital,
        reserves,
    )

    if ebit is None:
        ebit = operating_profit

    roce = return_on_capital_employed(
        ebit,
        equity_capital,
        reserves,
        borrowings,
    )

    roa = return_on_assets(
        net_profit,
        total_assets,
    )

    opm_mismatch_flag = opm_difference is not None and opm_difference > 1.0

    return {
        "net_profit_margin_pct": npm,
        "operating_profit_margin_pct": opm,
        "opm_difference": opm_difference,
        "opm_mismatch_flag": opm_mismatch_flag,
        "return_on_equity_pct": roe,
        "return_on_capital_employed_pct": roce,
        "return_on_assets_pct": roa,
    }


# ============================================================
# DAY 09 — LEVERAGE & EFFICIENCY
# ============================================================


def debt_to_equity(
    borrowings,
    equity_capital,
    reserves,
) -> float | None:
    """Process debt to equity."""
    borrowings = _to_float(borrowings)
    equity_capital = _to_float(equity_capital)
    reserves = _to_float(reserves)

    if borrowings is None or equity_capital is None or reserves is None:
        return None

    equity = equity_capital + reserves

    if borrowings == 0:
        return 0.0

    if equity <= 0:
        return None

    return borrowings / equity


def high_leverage_flag(
    debt_equity,
    broad_sector,
    threshold=5.0,
):
    """Process high leverage flag."""
    debt_equity = _to_float(debt_equity)

    if debt_equity is None:
        return False

    if broad_sector is not None and str(broad_sector).strip().lower() == "financials":
        return False

    return debt_equity > threshold


def interest_coverage_ratio(
    operating_profit,
    other_income,
    interest,
) -> float | None:
    """Process interest coverage ratio."""
    operating_profit = _to_float(operating_profit)
    other_income = _to_float(other_income)
    interest = _to_float(interest)

    if operating_profit is None or other_income is None or interest is None:
        return None

    if interest == 0:
        return None

    return (operating_profit + other_income) / interest


def interest_coverage_label(
    icr,
):
    """Process interest coverage label."""
    if icr is None:
        return "Debt Free"

    return None


def interest_coverage_warning(
    icr,
    threshold=1.5,
):
    """Process interest coverage warning."""
    if icr is None:
        return False

    return icr < threshold


def net_debt(
    borrowings,
    investments,
):
    """Process net debt."""
    borrowings = _to_float(borrowings)
    investments = _to_float(investments)

    if borrowings is None:
        borrowings = 0.0

    if investments is None:
        investments = 0.0

    return borrowings - investments


def asset_turnover(
    sales,
    total_assets,
) -> float | None:
    """Process asset turnover."""
    sales = _to_float(sales)
    total_assets = _to_float(total_assets)

    if sales is None or total_assets is None:
        return None

    if total_assets == 0:
        return None

    return sales / total_assets


def calculate_leverage_efficiency_ratios(
    borrowings,
    equity_capital,
    reserves,
    broad_sector,
    operating_profit,
    other_income,
    interest,
    investments,
    sales,
    total_assets,
):
    """Calculate leverage efficiency ratios."""
    de = debt_to_equity(
        borrowings,
        equity_capital,
        reserves,
    )

    high_leverage = high_leverage_flag(
        de,
        broad_sector,
    )

    icr = interest_coverage_ratio(
        operating_profit,
        other_income,
        interest,
    )

    return {
        "debt_to_equity": de,
        "high_leverage_flag": high_leverage,
        "interest_coverage": icr,
        "icr_label": interest_coverage_label(icr),
        "icr_warning_flag": interest_coverage_warning(icr),
        "net_debt": net_debt(
            borrowings,
            investments,
        ),
        "asset_turnover": asset_turnover(
            sales,
            total_assets,
        ),
    }
