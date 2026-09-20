import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import (
    get_cf,
    get_companies,
    get_pl,
    get_ratios,
    get_sectors,
)

st.set_page_config(
    page_title="Company Profile",
    page_icon="👤",
    layout="wide",
)

st.title("👤 Company Profile")
st.caption("Detailed financial profile for Nifty 100 companies")

# ---------------------------------------------------------
# LOAD MASTER DATA
# ---------------------------------------------------------

companies = get_companies()
sectors = get_sectors()

if companies.empty:
    st.error("Company master data is unavailable.")
    st.stop()

# ---------------------------------------------------------
# COMPANY SEARCH
# ---------------------------------------------------------

company_options = companies["id"].astype(str).tolist()

search_options = []

for _, row in companies.iterrows():
    ticker = str(row["id"])
    name = str(row.get("company_name", ""))
    search_options.append(f"{ticker} — {name}")

selected_display = st.selectbox(
    "Search company",
    search_options,
    index=0,
)

selected_ticker = selected_display.split(" — ")[0]

company_row = companies[companies["id"].astype(str) == selected_ticker].copy()

if company_row.empty:
    st.warning(f"Company ticker '{selected_ticker}' was not found.")
    st.stop()

company = company_row.iloc[0]

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------


def find_column(df, candidates):
    """Find column."""
    if df.empty:
        return None

    normalized = {str(col).lower().replace(" ", "_"): col for col in df.columns}

    for candidate in candidates:
        key = candidate.lower().replace(" ", "_")

        if key in normalized:
            return normalized[key]

    # Flexible partial matching
    for candidate in candidates:
        candidate_key = candidate.lower().replace(" ", "_")

        for normalized_key, original_column in normalized.items():
            if candidate_key in normalized_key:
                return original_column

    return None


def latest_value(df, candidates):
    """Process latest value."""
    column = find_column(df, candidates)

    if column is None or df.empty:
        return None

    values = pd.to_numeric(
        df[column],
        errors="coerce",
    ).dropna()

    if values.empty:
        return None

    return float(values.iloc[-1])


def format_metric(value, suffix=""):
    """Format metric."""
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.2f}{suffix}"


# ---------------------------------------------------------
# COMPANY INFORMATION
# ---------------------------------------------------------

company_name = str(company.get("company_name", selected_ticker))

st.subheader(company_name)

info1, info2, info3 = st.columns(3)

with info1:
    st.markdown("**NSE Ticker**")
    st.write(selected_ticker)

with info2:
    st.markdown("**Sector**")

    sector_match = sectors[sectors["company_id"].astype(str) == selected_ticker]

    if not sector_match.empty:
        sector_name = sector_match.iloc[0].get(
            "sector",
            "N/A",
        )
    else:
        sector_name = "N/A"

    st.write(sector_name)

with info3:
    st.markdown("**Sub-Sector / Industry**")

    if not sector_match.empty:
        industry = sector_match.iloc[0].get(
            "industry",
            "N/A",
        )
    else:
        industry = "N/A"

    st.write(industry)

about = company.get("about_company")

if about is not None and str(about).strip():
    st.info(str(about))

# ---------------------------------------------------------
# FINANCIAL DATA
# ---------------------------------------------------------

ratios = get_ratios(selected_ticker)
pl = get_pl(selected_ticker)
cf = get_cf(selected_ticker)

if ratios.empty:
    st.warning(f"No financial ratio data is available for {selected_ticker}.")

# ---------------------------------------------------------
# SIX KPI CARDS
# ---------------------------------------------------------

roe = latest_value(
    ratios,
    ["roe_pct", "roe_percentage", "return_on_equity_pct"],
)

roce = latest_value(
    ratios,
    ["roce_pct", "roce_percentage", "return_on_capital_employed_pct"],
)

npm = latest_value(
    ratios,
    [
        "npm_pct",
        "net_profit_margin_pct",
        "net_profit_margin",
        "profit_margin_pct",
    ],
)

de = latest_value(
    ratios,
    [
        "debt_to_equity",
        "debt_equity",
        "de_ratio",
    ],
)

revenue_cagr = latest_value(
    ratios,
    [
        "revenue_cagr_5y_pct",
        "revenue_cagr_5yr_pct",
        "revenue_5y_cagr_pct",
    ],
)

fcf = latest_value(
    ratios,
    [
        "free_cash_flow_cr",
        "fcf_cr",
        "free_cash_flow",
    ],
)

st.subheader("Key Financial Metrics")

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.metric("ROE", format_metric(roe, "%"))

with k2:
    st.metric("ROCE", format_metric(roce, "%"))

with k3:
    st.metric("Net Profit Margin", format_metric(npm, "%"))

with k4:
    st.metric("Debt / Equity", format_metric(de))

with k5:
    st.metric("Revenue CAGR 5Y", format_metric(revenue_cagr, "%"))

with k6:
    st.metric("Free Cash Flow", format_metric(fcf, " Cr"))

st.divider()

# ---------------------------------------------------------
# REVENUE / NET PROFIT — 10 YEAR BAR CHART
# ---------------------------------------------------------

st.subheader("10-Year Revenue & Net Profit")

if not pl.empty:

    year_column = find_column(
        pl,
        ["year", "financial_year"],
    )

    revenue_column = find_column(
        pl,
        [
            "revenue",
            "revenue_cr",
            "sales",
            "sales_cr",
        ],
    )

    profit_column = find_column(
        pl,
        [
            "net_profit",
            "net_profit_cr",
            "profit_after_tax",
            "pat",
            "profit",
        ],
    )

    if (
        year_column is not None
        and revenue_column is not None
        and profit_column is not None
    ):

        chart_df = pl[
            [
                year_column,
                revenue_column,
                profit_column,
            ]
        ].copy()

        chart_df[year_column] = pd.to_numeric(
            chart_df[year_column],
            errors="coerce",
        )

        chart_df[revenue_column] = pd.to_numeric(
            chart_df[revenue_column],
            errors="coerce",
        )

        chart_df[profit_column] = pd.to_numeric(
            chart_df[profit_column],
            errors="coerce",
        )

        chart_df = (
            chart_df.dropna(subset=[year_column]).sort_values(year_column).tail(10)
        )

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=chart_df[year_column],
                y=chart_df[revenue_column],
                name="Revenue",
            )
        )

        fig.add_trace(
            go.Bar(
                x=chart_df[year_column],
                y=chart_df[profit_column],
                name="Net Profit",
            )
        )

        fig.update_layout(
            barmode="group",
            height=450,
            xaxis_title="Year",
            yaxis_title="Amount",
            legend_title="Metric",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    else:
        st.info("Revenue or net profit columns are unavailable " "for this company.")

else:
    st.info("Profit & Loss data is unavailable.")

st.divider()

# ---------------------------------------------------------
# ROE / ROCE DUAL AXIS LINE
# ---------------------------------------------------------

st.subheader("ROE vs ROCE")

if not ratios.empty:

    year_column = find_column(
        ratios,
        ["year", "financial_year"],
    )

    roe_column = find_column(
        ratios,
        [
            "roe_pct",
            "roe_percentage",
            "return_on_equity_pct",
        ],
    )

    roce_column = find_column(
        ratios,
        [
            "roce_pct",
            "roce_percentage",
            "return_on_capital_employed_pct",
        ],
    )

    if year_column is not None and roe_column is not None and roce_column is not None:

        trend_df = ratios[
            [
                year_column,
                roe_column,
                roce_column,
            ]
        ].copy()

        trend_df[year_column] = pd.to_numeric(
            trend_df[year_column],
            errors="coerce",
        )

        trend_df[roe_column] = pd.to_numeric(
            trend_df[roe_column],
            errors="coerce",
        )

        trend_df[roce_column] = pd.to_numeric(
            trend_df[roce_column],
            errors="coerce",
        )

        trend_df = (
            trend_df.dropna(subset=[year_column]).sort_values(year_column).tail(10)
        )

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=trend_df[year_column],
                y=trend_df[roe_column],
                mode="lines+markers",
                name="ROE",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=trend_df[year_column],
                y=trend_df[roce_column],
                mode="lines+markers",
                name="ROCE",
                yaxis="y2",
            )
        )

        fig.update_layout(
            height=450,
            xaxis_title="Year",
            yaxis=dict(
                title="ROE (%)",
            ),
            yaxis2=dict(
                title="ROCE (%)",
                overlaying="y",
                side="right",
            ),
            legend_title="Metric",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    else:
        st.info("ROE/ROCE trend columns are unavailable.")

else:
    st.info("Ratio data is unavailable.")

st.divider()

# ---------------------------------------------------------
# PROS / CONS
# ---------------------------------------------------------

st.subheader("Company Snapshot")

snapshot_col1, snapshot_col2 = st.columns(2)

with snapshot_col1:
    st.markdown("### 🟢 Positive Indicators")

    positives = []

    if roe is not None and roe >= 15:
        positives.append(f"ROE is {roe:.2f}%.")

    if roce is not None and roce >= 15:
        positives.append(f"ROCE is {roce:.2f}%.")

    if de is not None and de <= 1:
        positives.append(f"Debt-to-equity is {de:.2f}.")

    if revenue_cagr is not None and revenue_cagr > 10:
        positives.append(f"5-year revenue CAGR is {revenue_cagr:.2f}%.")

    if fcf is not None and fcf > 0:
        positives.append(f"Free cash flow is positive at {fcf:.2f} Cr.")

    if positives:
        for item in positives:
            st.success(item)
    else:
        st.info("No positive indicators available.")

with snapshot_col2:
    st.markdown("### 🟠 Watch Indicators")

    concerns = []

    if roe is not None and roe < 10:
        concerns.append(f"ROE is {roe:.2f}%.")

    if roce is not None and roce < 10:
        concerns.append(f"ROCE is {roce:.2f}%.")

    if de is not None and de > 2:
        concerns.append(f"Debt-to-equity is {de:.2f}.")

    if revenue_cagr is not None and revenue_cagr < 5:
        concerns.append(f"5-year revenue CAGR is {revenue_cagr:.2f}%.")

    if fcf is not None and fcf < 0:
        concerns.append(f"Free cash flow is negative at {fcf:.2f} Cr.")

    if concerns:
        for item in concerns:
            st.warning(item)
    else:
        st.info("No major watch indicators available.")

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(f"Profile: {selected_ticker} | " "Data from Nifty 100 SQLite database")
