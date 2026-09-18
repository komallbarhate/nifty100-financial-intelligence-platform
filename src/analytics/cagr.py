from typing import Optional


# ============================================================
# DAY 10 — CAGR ENGINE
# ============================================================


VALID = None
DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
TURNAROUND = "TURNAROUND"
BOTH_NEGATIVE = "BOTH_NEGATIVE"
ZERO_BASE = "ZERO_BASE"
INSUFFICIENT = "INSUFFICIENT"


def calculate_cagr(
    start_value: Optional[float],
    end_value: Optional[float],
    years: int,
) -> tuple[Optional[float], Optional[str]]:
    """
    CAGR = ((End / Start) ^ (1 / n) - 1) * 100

    Handles all six required edge cases.

    Returns:
        (cagr_value, flag)
    """

    if years is None or years <= 0:
        return None, INSUFFICIENT

    if start_value is None or end_value is None:
        return None, INSUFFICIENT

    if start_value == 0:
        return None, ZERO_BASE

    if start_value > 0 and end_value > 0:
        cagr = (
            ((end_value / start_value) ** (1 / years)) - 1
        ) * 100

        return cagr, VALID

    if start_value > 0 and end_value < 0:
        return None, DECLINE_TO_LOSS

    if start_value < 0 and end_value > 0:
        return None, TURNAROUND

    if start_value < 0 and end_value < 0:
        return None, BOTH_NEGATIVE

    if end_value == 0:
        if start_value > 0:
            return None, DECLINE_TO_LOSS

        if start_value < 0:
            return None, BOTH_NEGATIVE

    return None, INSUFFICIENT


def has_required_years(
    available_years: list[int],
    start_year: int,
    end_year: int,
) -> bool:
    """
    Verify that both endpoint years exist.
    """

    if not available_years:
        return False

    available = set(available_years)

    return (
        start_year in available
        and end_year in available
    )


def calculate_window_cagr(
    yearly_values: dict[int, float],
    end_year: int,
    window_years: int,
) -> tuple[Optional[float], Optional[str]]:
    """
    Calculate CAGR using a fixed year window.

    Example:
        end_year = 2024
        window_years = 5

    Uses:
        start_year = 2019
        end_year   = 2024
    """

    start_year = end_year - window_years

    available_years = list(yearly_values.keys())

    if not has_required_years(
        available_years,
        start_year,
        end_year,
    ):
        return None, INSUFFICIENT

    return calculate_cagr(
        yearly_values[start_year],
        yearly_values[end_year],
        window_years,
    )


def calculate_all_cagr_windows(
    yearly_values: dict[int, float],
    end_year: int,
) -> dict:
    """
    Calculate 3-year, 5-year and 10-year CAGR.
    """

    result = {}

    for window in (3, 5, 10):
        value, flag = calculate_window_cagr(
            yearly_values,
            end_year,
            window,
        )

        result[f"cagr_{window}yr"] = value
        result[f"cagr_{window}yr_flag"] = flag

    return result


def calculate_company_growth_metrics(
    revenue: dict[int, float],
    pat: dict[int, float],
    eps: dict[int, float],
    end_year: int,
) -> dict:
    """
    Calculate Revenue, PAT and EPS CAGR for
    3-year, 5-year and 10-year windows.
    """

    result = {}

    for metric_name, values in (
        ("revenue", revenue),
        ("pat", pat),
        ("eps", eps),
    ):
        for window in (3, 5, 10):
            value, flag = calculate_window_cagr(
                values,
                end_year,
                window,
            )

            result[
                f"{metric_name}_cagr_{window}yr"
            ] = value

            result[
                f"{metric_name}_cagr_{window}yr_flag"
            ] = flag

    return result