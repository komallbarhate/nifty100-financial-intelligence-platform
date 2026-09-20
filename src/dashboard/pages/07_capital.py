import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_companies


st.set_page_config(
    page_title="Capital Allocation",
    page_icon="💰",
    layout="wide",
)

st.title("💰 Capital Allocation Map")
st.caption(
    "Interactive view of NIFTY 100 companies by their "
    "capital-allocation pattern."
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

CAPITAL_FILE = (
    PROJECT_ROOT
    / "output"
    / "capital_allocation.csv"
)


# =========================================================
# LOAD CAPITAL ALLOCATION
# =========================================================

@st.cache_data(ttl=600)
def load_capital_allocation():

    if not CAPITAL_FILE.exists():
        return pd.DataFrame()


    df = pd.read_csv(
        CAPITAL_FILE
    )


    required_columns = [
        "company_id",
        "year",
        "pattern_label",
    ]


    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]


    if missing:
        return pd.DataFrame()


    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.upper()
        .str.strip()
    )


    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )


    df["pattern_label"] = (
        df["pattern_label"]
        .fillna("No Data")
        .astype(str)
        .str.strip()
    )


    # -----------------------------------------------------
    # KEEP LATEST AVAILABLE YEAR FOR EACH COMPANY
    # -----------------------------------------------------

    df = (
        df
        .sort_values(
            [
                "company_id",
                "year",
            ]
        )
        .drop_duplicates(
            "company_id",
            keep="last",
        )
    )


    # -----------------------------------------------------
    # COMPANY MASTER
    # -----------------------------------------------------

    companies = get_companies().copy()


    companies["company_id"] = (
        companies["id"]
        .astype(str)
        .str.upper()
        .str.strip()
    )


    companies = companies[
        [
            "company_id",
            "company_name",
        ]
    ]


    df = df.merge(
        companies,
        on="company_id",
        how="left",
    )


    df["company_name"] = (
        df["company_name"]
        .fillna(df["company_id"])
    )


    return df[
        [
            "company_id",
            "company_name",
            "year",
            "pattern_label",
        ]
    ].copy()


allocation = load_capital_allocation()


# =========================================================
# VALIDATION
# =========================================================

if allocation.empty:

    st.error(
        "Capital allocation data could not be loaded."
    )

    st.info(
        "The dashboard could not read "
        "output/capital_allocation.csv."
    )

    st.stop()


# =========================================================
# HEADER KPIs
# =========================================================

total_companies = (
    allocation["company_id"]
    .nunique()
)


total_patterns = (
    allocation["pattern_label"]
    .nunique()
)


latest_year = (
    int(allocation["year"].max())
    if allocation["year"].notna().any()
    else "N/A"
)


col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "Companies",
        total_companies,
    )


with col2:

    st.metric(
        "Allocation Patterns",
        total_patterns,
    )


with col3:

    st.metric(
        "Latest Year",
        latest_year,
    )


st.divider()


# =========================================================
# PATTERN SUMMARY
# =========================================================

st.subheader(
    "Capital Allocation Patterns"
)


pattern_summary = (
    allocation
    .groupby("pattern_label")
    .size()
    .reset_index(
        name="Companies"
    )
    .sort_values(
        "Companies",
        ascending=False,
    )
)


# =========================================================
# TREEMAP
# =========================================================

fig = px.treemap(
    pattern_summary,
    path=[
        "pattern_label"
    ],
    values="Companies",
    title=(
        "NIFTY 100 Companies by "
        "Capital Allocation Pattern"
    ),
)


fig.update_traces(
    textinfo="label+value+percent parent",
)


fig.update_layout(
    height=600,
    margin=dict(
        t=60,
        l=10,
        r=10,
        b=10,
    ),
)


st.plotly_chart(
    fig,
    use_container_width=True,
)


st.caption(
    "Each rectangle represents the number of companies "
    "in that capital-allocation pattern."
)


st.divider()


# =========================================================
# PATTERN FILTER
# =========================================================

st.subheader(
    "Explore Companies by Pattern"
)


patterns = sorted(
    allocation[
        "pattern_label"
    ]
    .dropna()
    .unique()
    .tolist()
)


selected_pattern = st.selectbox(
    "Select capital-allocation pattern",
    ["All Patterns"] + patterns,
)


if selected_pattern == "All Patterns":

    filtered = allocation.copy()

else:

    filtered = allocation[
        allocation[
            "pattern_label"
        ]
        == selected_pattern
    ].copy()


# =========================================================
# PATTERN KPI
# =========================================================

if selected_pattern != "All Patterns":

    st.info(
        f"{selected_pattern}: "
        f"{len(filtered)} companies"
    )


# =========================================================
# COMPANY TABLE
# =========================================================

display_df = (
    filtered[
        [
            "company_id",
            "company_name",
            "year",
            "pattern_label",
        ]
    ]
    .rename(
        columns={
            "company_id":
                "Ticker",

            "company_name":
                "Company",

            "year":
                "Year",

            "pattern_label":
                "Capital Allocation Pattern",
        }
    )
    .sort_values(
        "Company"
    )
    .reset_index(
        drop=True
    )
)


st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)


# =========================================================
# CSV DOWNLOAD
# =========================================================

csv_data = display_df.to_csv(
    index=False
).encode(
    "utf-8"
)


st.download_button(
    label="⬇️ Download Company List CSV",
    data=csv_data,
    file_name=(
        "capital_allocation_companies.csv"
    ),
    mime="text/csv",
)


st.divider()


# =========================================================
# PATTERN DISTRIBUTION
# =========================================================

st.subheader(
    "Pattern Distribution"
)


distribution = (
    allocation[
        "pattern_label"
    ]
    .value_counts()
    .reset_index()
)


distribution.columns = [
    "Pattern",
    "Companies",
]


fig2 = px.bar(
    distribution,
    x="Pattern",
    y="Companies",
    text="Companies",
    title=(
        "Companies per Capital Allocation Pattern"
    ),
)


fig2.update_layout(
    height=450,
    xaxis_title="",
    yaxis_title="Number of Companies",
)


fig2.update_traces(
    textposition="outside"
)


st.plotly_chart(
    fig2,
    use_container_width=True,
)


st.caption(
    "Patterns are taken directly from the Sprint 2 "
    "capital-allocation output."
)
