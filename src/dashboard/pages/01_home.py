import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import (
    get_all_latest_ratios,
    get_all_latest_valuations,
    get_companies,
    get_sectors,
)

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
)

st.title("🏠 Nifty 100 Analytics")
st.caption("Financial Intelligence Platform — Nifty 100 overview")

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

companies = get_companies()
ratios = get_all_latest_ratios()
valuations = get_all_latest_valuations()
sectors = get_sectors()

if companies.empty:
    st.error("Company data is unavailable.")
    st.stop()

# ---------------------------------------------------------
# YEAR SELECTOR
# ---------------------------------------------------------

available_years = (
    sorted(ratios["year"].dropna().astype(int).unique().tolist())
    if not ratios.empty
    else []
)

selected_year = st.sidebar.selectbox(
    "Analysis Year",
    available_years,
    index=len(available_years) - 1 if available_years else 0,
)

# ---------------------------------------------------------
# SELECT YEAR DATA
# ---------------------------------------------------------

year_ratios = ratios.copy()

if not year_ratios.empty and "year" in year_ratios.columns:
    year_ratios = year_ratios[
        year_ratios["year"].astype(int) == int(selected_year)
    ].copy()

# If selected year has no rows, use latest available ratios
if year_ratios.empty:
    year_ratios = ratios.copy()

# ---------------------------------------------------------
# HELPER
# ---------------------------------------------------------


def numeric_median(df, column):
    """Process numeric median."""
    if column not in df.columns:
        return None

    values = pd.to_numeric(df[column], errors="coerce").dropna()

    if values.empty:
        return None

    return float(values.median())


def numeric_mean(df, column):
    """Process numeric mean."""
    if column not in df.columns:
        return None

    values = pd.to_numeric(df[column], errors="coerce").dropna()

    if values.empty:
        return None

    return float(values.mean())


def format_value(value, suffix=""):
    """Format value."""
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.2f}{suffix}"


# ---------------------------------------------------------
# KPI VALUES
# ---------------------------------------------------------

average_roe = numeric_mean(year_ratios, "roe_pct")

median_pe = numeric_median(valuations, "pe_ratio")

median_de = numeric_median(year_ratios, "debt_to_equity")

total_companies = companies["id"].nunique()

median_revenue_cagr = numeric_median(year_ratios, "revenue_cagr_5y_pct")

if "debt_to_equity" in year_ratios.columns:
    debt_values = pd.to_numeric(
        year_ratios["debt_to_equity"],
        errors="coerce",
    )

    debt_free_count = int((debt_values.fillna(999999) <= 0).sum())
else:
    debt_free_count = 0

# ---------------------------------------------------------
# KPI TILES
# ---------------------------------------------------------

st.subheader(f"Market Overview — {selected_year}")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        "Average ROE",
        format_value(average_roe, "%"),
    )

with col2:
    st.metric(
        "Median P/E",
        format_value(median_pe),
    )

with col3:
    st.metric(
        "Median D/E",
        format_value(median_de),
    )

with col4:
    st.metric(
        "Total Companies",
        f"{total_companies}",
    )

with col5:
    st.metric(
        "Median Revenue CAGR 5Y",
        format_value(median_revenue_cagr, "%"),
    )

with col6:
    st.metric(
        "Debt-Free Companies",
        f"{debt_free_count}",
    )

st.divider()

# ---------------------------------------------------------
# SECTOR BREAKDOWN
# ---------------------------------------------------------

st.subheader("Sector Breakdown")

if not sectors.empty and "sector" in sectors.columns:

    sector_counts = (
        sectors.groupby("sector")["company_id"]
        .nunique()
        .reset_index(name="companies")
        .sort_values("companies", ascending=False)
    )

    col1, col2 = st.columns([1.2, 1])

    with col1:
        fig = px.pie(
            sector_counts,
            names="sector",
            values="companies",
            hole=0.55,
            title="Nifty 100 Companies by Sector",
        )

        fig.update_layout(
            height=450,
            margin=dict(l=20, r=20, t=60, b=20),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    with col2:
        st.dataframe(
            sector_counts,
            use_container_width=True,
            hide_index=True,
        )

else:
    st.info("Sector data is unavailable.")

st.divider()

# ---------------------------------------------------------
# TOP 5 QUALITY COMPANIES
# ---------------------------------------------------------

st.subheader("Top 5 Quality Companies")

quality_columns = [
    "company_id",
    "roe_pct",
    "roce_pct",
    "revenue_cagr_5y_pct",
    "pat_cagr_5y_pct",
    "debt_to_equity",
    "interest_coverage_ratio",
]

available_quality_columns = [
    column for column in quality_columns if column in year_ratios.columns
]

if "company_id" in year_ratios.columns and len(available_quality_columns) > 1:

    quality = year_ratios[available_quality_columns].copy()

    # Convert metric columns to numeric
    for column in available_quality_columns:
        if column != "company_id":
            quality[column] = pd.to_numeric(
                quality[column],
                errors="coerce",
            )

    metric_columns = [
        column for column in available_quality_columns if column != "company_id"
    ]

    # Percentile-based composite quality score
    for column in metric_columns:
        quality[f"{column}_pctile"] = quality[column].rank(pct=True) * 100

    # Reverse D/E because lower debt is preferable
    if "debt_to_equity_pctile" in quality.columns:
        quality["debt_to_equity_pctile"] = 100 - quality["debt_to_equity_pctile"]

    percentile_columns = [
        column for column in quality.columns if column.endswith("_pctile")
    ]

    quality["composite_quality_score"] = quality[percentile_columns].mean(axis=1)

    quality = quality.sort_values(
        "composite_quality_score",
        ascending=False,
    ).head(5)

    quality = quality.merge(
        companies[["id", "company_name"]],
        left_on="company_id",
        right_on="id",
        how="left",
    )

    display_columns = [
        "company_id",
        "company_name",
        "composite_quality_score",
    ]

    st.dataframe(
        quality[display_columns]
        .rename(
            columns={
                "company_id": "Ticker",
                "company_name": "Company",
                "composite_quality_score": "Quality Score",
            }
        )
        .style.format({"Quality Score": "{:.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

else:
    st.info(
        "Quality score cannot be calculated because the required "
        "financial ratio columns are unavailable."
    )

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    "Data source: Nifty 100 project SQLite database | " "Dashboard cache: 10 minutes"
)
