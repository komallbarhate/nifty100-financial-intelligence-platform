import sqlite3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_companies


st.set_page_config(
    page_title="Trends | Nifty 100 Analytics",
    page_icon="T",
    layout="wide"
)

st.title("Financial Trends")
st.caption("Analyze a company's financial performance over the last 10 years.")


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"


@st.cache_data(ttl=600)
def get_company_trend_data(ticker):

    conn = sqlite3.connect(DB_PATH)

    pl = pd.read_sql_query(
        """
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year
        """,
        conn,
        params=[ticker]
    )

    ratios = pd.read_sql_query(
        """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year
        """,
        conn,
        params=[ticker]
    )

    bs = pd.read_sql_query(
        """
        SELECT *
        FROM balancesheet
        WHERE company_id = ?
        ORDER BY year
        """,
        conn,
        params=[ticker]
    )

    cf = pd.read_sql_query(
        """
        SELECT *
        FROM cashflow
        WHERE company_id = ?
        ORDER BY year
        """,
        conn,
        params=[ticker]
    )

    conn.close()

    return pl, ratios, bs, cf


# ---------------------------------------------------------
# LOAD COMPANIES
# ---------------------------------------------------------
companies = get_companies()

if companies.empty:
    st.error("Company data could not be loaded.")
    st.stop()


company_map = (
    companies[
        ["id", "company_name"]
    ]
    .dropna()
    .drop_duplicates()
    .sort_values("company_name")
)

company_options = company_map["id"].tolist()


# ---------------------------------------------------------
# COMPANY SELECTOR
# ---------------------------------------------------------
selected_company = st.selectbox(
    "Search company",
    company_options,
    format_func=lambda x: (
        f"{x} — "
        f"{company_map.loc[company_map['id'] == x, 'company_name'].iloc[0]}"
    )
)


company_name = company_map.loc[
    company_map["id"] == selected_company,
    "company_name"
].iloc[0]


st.subheader(company_name)
st.caption(f"NSE Ticker: {selected_company}")


# ---------------------------------------------------------
# LOAD COMPANY DATA
# ---------------------------------------------------------
pl, ratios, bs, cf = get_company_trend_data(
    selected_company
)


if pl.empty and ratios.empty and bs.empty and cf.empty:
    st.warning(
        "No financial trend data is available for this company."
    )
    st.stop()


# ---------------------------------------------------------
# PREPARE DATA
# ---------------------------------------------------------
if not pl.empty:
    pl["year"] = pd.to_numeric(
        pl["year"],
        errors="coerce"
    )

if not ratios.empty:
    ratios["year"] = pd.to_numeric(
        ratios["year"],
        errors="coerce"
    )

if not bs.empty:
    bs["year"] = pd.to_numeric(
        bs["year"],
        errors="coerce"
    )

if not cf.empty:
    cf["year"] = pd.to_numeric(
        cf["year"],
        errors="coerce"
    )


# ---------------------------------------------------------
# AVAILABLE METRICS
# ---------------------------------------------------------
metric_options = {}


# Profit & Loss metrics
if not pl.empty:

    if "sales" in pl.columns:
        metric_options["Revenue"] = (
            pl,
            "sales",
            "Revenue"
        )

    if "net_profit" in pl.columns:
        metric_options["Net Profit"] = (
            pl,
            "net_profit",
            "Net Profit"
        )

    if "operating_profit" in pl.columns:
        metric_options["Operating Profit"] = (
            pl,
            "operating_profit",
            "Operating Profit"
        )

    if "eps" in pl.columns:
        metric_options["EPS"] = (
            pl,
            "eps",
            "EPS"
        )

    if "opm_percentage" in pl.columns:
        metric_options["Operating Margin"] = (
            pl,
            "opm_percentage",
            "Operating Margin"
        )


# Financial ratio metrics
if not ratios.empty:

    ratio_candidates = [
        (
            "return_on_equity_pct",
            "ROE",
            "ROE"
        ),
        (
            "roe",
            "ROE",
            "ROE"
        ),
        (
            "return_on_capital_employed_pct",
            "ROCE",
            "ROCE"
        ),
        (
            "roce",
            "ROCE",
            "ROCE"
        ),
        (
            "net_profit_margin_pct",
            "Net Profit Margin",
            "Net Profit Margin"
        ),
        (
            "npm",
            "Net Profit Margin",
            "Net Profit Margin"
        ),
        (
            "operating_profit_margin_pct",
            "Operating Profit Margin",
            "Operating Profit Margin"
        ),
        (
            "opm",
            "Operating Profit Margin",
            "Operating Profit Margin"
        ),
        (
            "debt_to_equity",
            "Debt to Equity",
            "Debt to Equity"
        ),
        (
            "interest_coverage",
            "Interest Coverage",
            "Interest Coverage"
        ),
        (
            "current_ratio",
            "Current Ratio",
            "Current Ratio"
        ),
        (
            "pe_ratio",
            "P/E",
            "P/E"
        ),
        (
            "pb_ratio",
            "P/B",
            "P/B"
        ),
        (
            "dividend_yield",
            "Dividend Yield",
            "Dividend Yield"
        ),
    ]

    for column, label, display_name in ratio_candidates:

        if column in ratios.columns:
            metric_options[label] = (
                ratios,
                column,
                display_name
            )


# Cash flow metrics
if not cf.empty:

    if "operating_activity" in cf.columns:
        metric_options["Operating Cash Flow"] = (
            cf,
            "operating_activity",
            "Operating Cash Flow"
        )

    if "net_cash_flow" in cf.columns:
        metric_options["Net Cash Flow"] = (
            cf,
            "net_cash_flow",
            "Net Cash Flow"
        )


# Balance sheet metrics
if not bs.empty:

    if "borrowings" in bs.columns:
        metric_options["Borrowings"] = (
            bs,
            "borrowings",
            "Borrowings"
        )

    if "reserves" in bs.columns:
        metric_options["Reserves"] = (
            bs,
            "reserves",
            "Reserves"
        )


# Remove duplicate labels while preserving order
metric_options = dict(metric_options)


if not metric_options:
    st.warning(
        "No compatible financial metrics were found for this company."
    )
    st.stop()


# ---------------------------------------------------------
# METRIC SELECTOR
# ---------------------------------------------------------
st.subheader("Trend Metrics")

selected_metrics = st.multiselect(
    "Select up to 3 metrics",
    options=list(metric_options.keys()),
    default=list(metric_options.keys())[:3],
    max_selections=3
)


if not selected_metrics:
    st.info("Select at least one metric to display the trend.")
    st.stop()


# ---------------------------------------------------------
# BUILD TREND DATA
# ---------------------------------------------------------
trend_frames = []

for metric in selected_metrics:

    source_df, column, display_name = metric_options[metric]

    if source_df.empty:
        continue

    temp = source_df[
        ["year", column]
    ].copy()

    temp[column] = pd.to_numeric(
        temp[column],
        errors="coerce"
    )

    temp = temp.dropna(
        subset=["year", column]
    )

    temp = temp.sort_values("year")

    # Keep latest 10 available years
    temp = temp.tail(10)

    temp["metric"] = display_name
    temp["value"] = temp[column]

    trend_frames.append(
        temp[
            ["year", "metric", "value"]
        ]
    )


if not trend_frames:
    st.warning(
        "No numeric data is available for the selected metrics."
    )
    st.stop()


trend_data = pd.concat(
    trend_frames,
    ignore_index=True
)

trend_data["year"] = trend_data[
    "year"
].astype(int)


# ---------------------------------------------------------
# TREND CHART
# ---------------------------------------------------------
st.subheader("10-Year Financial Trend")

fig = go.Figure()


for metric in selected_metrics:

    metric_data = trend_data[
        trend_data["metric"] == metric
    ].sort_values("year")

    if metric_data.empty:
        continue

    fig.add_trace(
        go.Scatter(
            x=metric_data["year"],
            y=metric_data["value"],
            mode="lines+markers",
            name=metric,
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "Year: %{x}<br>"
                "Value: %{y:.2f}"
                "<extra></extra>"
            )
        )
    )


fig.update_layout(
    height=600,
    xaxis_title="Year",
    yaxis_title="Value",
    hovermode="x unified",
    legend_title="Metric"
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ---------------------------------------------------------
# YOY CHANGES
# ---------------------------------------------------------
st.subheader("Year-over-Year Changes")

for metric in selected_metrics:

    metric_data = trend_data[
        trend_data["metric"] == metric
    ].sort_values("year").copy()

    if len(metric_data) < 2:
        continue

    metric_data["YoY Change %"] = (
        metric_data["value"].pct_change() * 100
    )

    metric_data["YoY Change %"] = (
        metric_data["YoY Change %"]
        .replace(
            [float("inf"), float("-inf")],
            pd.NA
        )
    )

    st.markdown(f"**{metric}**")

    yoy_table = metric_data[
        ["year", "value", "YoY Change %"]
    ].copy()

    yoy_table = yoy_table.rename(
        columns={
            "year": "Year",
            "value": "Value",
            "YoY Change %": "YoY Change %"
        }
    )

    st.dataframe(
        yoy_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Value": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "YoY Change %": st.column_config.NumberColumn(
                format="%.2f%%"
            )
        }
    )


# ---------------------------------------------------------
# DATA TABLE
# ---------------------------------------------------------
st.subheader("Trend Data")

pivot = trend_data.pivot(
    index="year",
    columns="metric",
    values="value"
).reset_index()

pivot = pivot.rename(
    columns={"year": "Year"}
)

st.dataframe(
    pivot,
    use_container_width=True,
    hide_index=True
)
