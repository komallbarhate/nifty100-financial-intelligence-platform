import pandas as pd
import streamlit as st

from src.dashboard.utils.db import (
    get_all_latest_ratios,
    get_all_latest_valuations,
    get_companies,
    get_sectors,
)
from src.screener.composite_score import CompositeScorer

st.set_page_config(
    page_title="Nifty 100 Screener",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 Nifty 100 Screener")
st.caption(
    "Filter Nifty 100 companies using financial quality, "
    "growth, leverage and valuation metrics."
)


# =========================================================
# LOAD DATA
# =========================================================


@st.cache_data(ttl=600)
def load_screener_data():
    """Load screener data."""
    companies = get_companies()
    ratios = get_all_latest_ratios()
    valuations = get_all_latest_valuations()
    sectors = get_sectors()

    if companies.empty:
        return pd.DataFrame()

    # -----------------------------------------------------
    # Clean company IDs
    # -----------------------------------------------------

    for frame in [companies, ratios, valuations, sectors]:

        if "id" in frame.columns:
            frame["id"] = frame["id"].astype(str).str.strip().str.upper()

        if "company_id" in frame.columns:
            frame["company_id"] = (
                frame["company_id"].astype(str).str.strip().str.upper()
            )

    # -----------------------------------------------------
    # Start with company master
    # -----------------------------------------------------

    df = companies[["id", "company_name"]].copy()

    df = df.rename(columns={"id": "company_id"})

    # -----------------------------------------------------
    # Latest financial ratios
    # -----------------------------------------------------

    if not ratios.empty:

        ratio_data = ratios.copy()

        ratio_data = ratio_data.drop_duplicates(
            subset=["company_id"],
            keep="last",
        )

        df = df.merge(
            ratio_data,
            on="company_id",
            how="left",
            suffixes=("", "_ratio"),
        )

    # -----------------------------------------------------
    # Latest valuation data
    # -----------------------------------------------------

    if not valuations.empty:

        valuation_data = valuations.copy()

        valuation_data = valuation_data.drop_duplicates(
            subset=["company_id"],
            keep="last",
        )

        valuation_columns = [
            "company_id",
            "market_cap_crore",
            "enterprise_value_crore",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield_pct",
        ]

        available = [
            column for column in valuation_columns if column in valuation_data.columns
        ]

        df = df.merge(
            valuation_data[available],
            on="company_id",
            how="left",
            suffixes=("", "_valuation"),
        )

    # -----------------------------------------------------
    # Sector information
    # -----------------------------------------------------

    if not sectors.empty:

        sector_data = sectors[
            [
                "company_id",
                "sector",
                "industry",
            ]
        ].drop_duplicates(subset=["company_id"])

        df = df.merge(
            sector_data,
            on="company_id",
            how="left",
        )

    # -----------------------------------------------------
    # Numeric conversion
    # -----------------------------------------------------

    numeric_columns = [
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "debt_to_equity",
        "interest_coverage",
        "free_cash_flow_cr",
        "cash_from_operations_cr",
        "cfo_pat_ratio",
        "revenue_cagr_3yr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "pe_ratio",
        "pb_ratio",
        "dividend_yield_pct",
        "market_cap_crore",
        "enterprise_value_crore",
        "eps_cagr_5yr",
        "asset_turnover",
        "dividend_payout_ratio_pct",
        "earnings_per_share",
        "book_value_per_share",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    # -----------------------------------------------------
    # Add Sprint 3 composite score
    # -----------------------------------------------------

    try:

        scorer = CompositeScorer()

        scores = scorer.calculate()

        score_columns = [
            "company_id",
            "sprint3_composite_score",
        ]

        available_scores = [
            column for column in score_columns if column in scores.columns
        ]

        if len(available_scores) == 2:

            scores = scores[available_scores].drop_duplicates(subset=["company_id"])

            scores["company_id"] = (
                scores["company_id"].astype(str).str.strip().str.upper()
            )

            df = df.drop(
                columns=["sprint3_composite_score"],
                errors="ignore",
            )

            df = df.merge(
                scores,
                on="company_id",
                how="left",
            )

    except Exception:
        # Dashboard should continue even if the
        # optional composite-score calculation fails.
        df["sprint3_composite_score"] = pd.NA

    return df


try:

    df = load_screener_data()

except Exception as error:

    st.error("Unable to load screener data.")
    st.exception(error)
    st.stop()


if df.empty:

    st.warning("No screener data is available.")

    st.stop()


# =========================================================
# FILTER HELPERS
# =========================================================


def apply_minimum(
    frame,
    column,
    threshold,
):
    """Apply minimum."""
    if column not in frame.columns:
        return frame

    values = pd.to_numeric(
        frame[column],
        errors="coerce",
    )

    return frame[values.notna() & (values >= threshold)].copy()


def apply_maximum(
    frame,
    column,
    threshold,
):
    """Apply maximum."""
    if column not in frame.columns:
        return frame

    values = pd.to_numeric(
        frame[column],
        errors="coerce",
    )

    return frame[values.notna() & (values <= threshold)].copy()


# =========================================================
# PRESET DEFINITIONS
# =========================================================

PRESETS = {
    "Quality Compounder": {
        "roe_min": 15.0,
        "de_max": 1.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 10.0,
        "pat_cagr_min": 0.0,
        "opm_min": 0.0,
        "pe_max": 100.0,
        "pb_max": 100.0,
        "dividend_min": 0.0,
        "icr_min": 0.0,
    },
    "Value Pick": {
        "roe_min": 0.0,
        "de_max": 2.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 0.0,
        "pe_max": 20.0,
        "pb_max": 3.0,
        "dividend_min": 1.0,
        "icr_min": 0.0,
    },
    "Growth Accelerator": {
        "roe_min": 0.0,
        "de_max": 2.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 15.0,
        "pat_cagr_min": 20.0,
        "opm_min": 0.0,
        "pe_max": 100.0,
        "pb_max": 100.0,
        "dividend_min": 0.0,
        "icr_min": 0.0,
    },
    "Dividend Champion": {
        "roe_min": 0.0,
        "de_max": 100.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 0.0,
        "pe_max": 100.0,
        "pb_max": 100.0,
        "dividend_min": 2.0,
        "icr_min": 0.0,
    },
    "Debt-Free Blue Chip": {
        "roe_min": 12.0,
        "de_max": 0.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 0.0,
        "pe_max": 100.0,
        "pb_max": 100.0,
        "dividend_min": 0.0,
        "icr_min": 0.0,
    },
    "Turnaround Watch": {
        "roe_min": 0.0,
        "de_max": 100.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 0.0,
        "pe_max": 100.0,
        "pb_max": 100.0,
        "dividend_min": 0.0,
        "icr_min": 0.0,
    },
}


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "roe_min": 0.0,
    "de_max": 100.0,
    "fcf_min": 0.0,
    "revenue_cagr_min": 0.0,
    "pat_cagr_min": 0.0,
    "opm_min": 0.0,
    "pe_max": 100.0,
    "pb_max": 100.0,
    "dividend_min": 0.0,
    "icr_min": 0.0,
    "active_preset": "Custom",
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# PRESETS
# =========================================================

st.subheader("Quick Presets")

preset_columns = st.columns(6)

for index, preset_name in enumerate(PRESETS):

    with preset_columns[index]:

        if st.button(
            preset_name,
            key=f"preset_{index}",
            use_container_width=True,
        ):

            values = PRESETS[preset_name]

            for key, value in values.items():
                st.session_state[key] = value

            st.session_state["active_preset"] = preset_name

            st.rerun()


st.caption(f"Active preset: " f"**{st.session_state['active_preset']}**")


st.divider()


# =========================================================
# TEN FILTER SLIDERS
# =========================================================

st.subheader("Screening Filters")

left, right = st.columns(2)


with left:

    st.slider(
        "ROE minimum (%)",
        min_value=0.0,
        max_value=50.0,
        step=0.5,
        key="roe_min",
    )

    st.slider(
        "Debt / Equity maximum",
        min_value=0.0,
        max_value=100.0,
        step=0.05,
        key="de_max",
    )

    st.slider(
        "Free Cash Flow minimum (Cr)",
        min_value=-10000.0,
        max_value=10000.0,
        step=100.0,
        key="fcf_min",
    )

    st.slider(
        "Revenue CAGR 5Y minimum (%)",
        min_value=-50.0,
        max_value=100.0,
        step=1.0,
        key="revenue_cagr_min",
    )

    st.slider(
        "PAT CAGR 5Y minimum (%)",
        min_value=-100.0,
        max_value=150.0,
        step=1.0,
        key="pat_cagr_min",
    )


with right:

    st.slider(
        "Operating Profit Margin minimum (%)",
        min_value=-50.0,
        max_value=100.0,
        step=1.0,
        key="opm_min",
    )

    st.slider(
        "P/E maximum",
        min_value=0.0,
        max_value=200.0,
        step=1.0,
        key="pe_max",
    )

    st.slider(
        "P/B maximum",
        min_value=0.0,
        max_value=100.0,
        step=0.5,
        key="pb_max",
    )

    st.slider(
        "Dividend Yield minimum (%)",
        min_value=0.0,
        max_value=20.0,
        step=0.25,
        key="dividend_min",
    )

    st.slider(
        "Interest Coverage minimum",
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        key="icr_min",
    )


# =========================================================
# APPLY FILTERS
# =========================================================

filtered = df.copy()

filtered = apply_minimum(
    filtered,
    "return_on_equity_pct",
    st.session_state["roe_min"],
)

filtered = apply_maximum(
    filtered,
    "debt_to_equity",
    st.session_state["de_max"],
)

filtered = apply_minimum(
    filtered,
    "free_cash_flow_cr",
    st.session_state["fcf_min"],
)

filtered = apply_minimum(
    filtered,
    "revenue_cagr_5yr",
    st.session_state["revenue_cagr_min"],
)

filtered = apply_minimum(
    filtered,
    "pat_cagr_5yr",
    st.session_state["pat_cagr_min"],
)

filtered = apply_minimum(
    filtered,
    "operating_profit_margin_pct",
    st.session_state["opm_min"],
)

filtered = apply_maximum(
    filtered,
    "pe_ratio",
    st.session_state["pe_max"],
)

filtered = apply_maximum(
    filtered,
    "pb_ratio",
    st.session_state["pb_max"],
)

filtered = apply_minimum(
    filtered,
    "dividend_yield_pct",
    st.session_state["dividend_min"],
)

filtered = apply_minimum(
    filtered,
    "interest_coverage",
    st.session_state["icr_min"],
)


# =========================================================
# RESULTS SUMMARY
# =========================================================

st.divider()

st.subheader("Screening Results")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Companies Matching",
        len(filtered),
    )

with col2:
    st.metric(
        "Total Universe",
        df["company_id"].nunique(),
    )

with col3:

    if "sprint3_composite_score" in filtered.columns and not filtered.empty:

        average_score = pd.to_numeric(
            filtered["sprint3_composite_score"],
            errors="coerce",
        ).mean()

        if pd.isna(average_score):
            score_text = "N/A"
        else:
            score_text = f"{average_score:.2f}"

    else:
        score_text = "N/A"

    st.metric(
        "Average Composite Score",
        score_text,
    )


# =========================================================
# RESULTS TABLE
# =========================================================

display_columns = [
    "company_id",
    "company_name",
    "sector",
    "sprint3_composite_score",
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin_pct",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
    "interest_coverage",
]

available_columns = [column for column in display_columns if column in filtered.columns]


if filtered.empty:

    st.warning(
        "No companies match the current filters. " "Reduce one or more thresholds."
    )

    export_df = pd.DataFrame(columns=available_columns)

else:

    export_df = filtered[available_columns].copy()

    if "sprint3_composite_score" in export_df.columns:

        export_df = export_df.sort_values(
            "sprint3_composite_score",
            ascending=False,
            na_position="last",
        )

    rename_map = {
        "company_id": "Ticker",
        "company_name": "Company",
        "sector": "Sector",
        "sprint3_composite_score": "Composite Score",
        "return_on_equity_pct": "ROE %",
        "debt_to_equity": "D/E",
        "free_cash_flow_cr": "FCF Cr",
        "revenue_cagr_5yr": "Revenue CAGR 5Y %",
        "pat_cagr_5yr": "PAT CAGR 5Y %",
        "operating_profit_margin_pct": "OPM %",
        "pe_ratio": "P/E",
        "pb_ratio": "P/B",
        "dividend_yield_pct": "Dividend Yield %",
        "interest_coverage": "ICR",
    }

    export_df = export_df.rename(columns=rename_map)

    format_map = {
        column: "{:.2f}"
        for column in export_df.columns
        if column
        not in [
            "Ticker",
            "Company",
            "Sector",
        ]
    }

    st.dataframe(
        export_df.style.format(
            format_map,
            na_rep="N/A",
        ),
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# CSV EXPORT
# =========================================================

st.divider()

st.subheader("Export")

csv_bytes = export_df.to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇️ Download Screener Results CSV",
    data=csv_bytes,
    file_name="nifty100_screener_results.csv",
    mime="text/csv",
)

st.caption(
    "The composite score shown here uses the Sprint 3 "
    "sector-relative scoring engine."
)
