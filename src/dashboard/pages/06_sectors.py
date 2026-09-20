import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Sector Analysis | Nifty 100 Analytics",
    page_icon="S",
    layout="wide"
)

st.title("Sector Analysis")
st.caption("Compare companies across Nifty 100 sectors.")


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"


@st.cache_data(ttl=600)
def load_sector_data():

    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query(
        """
        SELECT id AS company_id, company_name
        FROM companies
        """,
        conn
    )

    sectors = pd.read_sql_query(
        """
        SELECT company_id, sector, industry
        FROM sectors
        """,
        conn
    )

    pl = pd.read_sql_query(
        """
        SELECT company_id, year, sales
        FROM profitandloss
        WHERE sales IS NOT NULL
        """,
        conn
    )

    ratios = pd.read_sql_query(
        """
        SELECT *
        FROM financial_ratios
        """,
        conn
    )

    market_cap = pd.read_sql_query(
        """
        SELECT company_id, year, market_cap_crore
        FROM market_cap
        """,
        conn
    )

    conn.close()

    # -----------------------------------------------------
    # Latest P&L
    # -----------------------------------------------------
    pl = pl.sort_values("year")

    latest_pl = (
        pl.groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    latest_pl = latest_pl[
        ["company_id", "sales", "year"]
    ].rename(
        columns={
            "sales": "revenue",
            "year": "latest_year"
        }
    )

    # -----------------------------------------------------
    # Revenue 5-year CAGR
    # -----------------------------------------------------
    pl["year"] = pd.to_numeric(
        pl["year"],
        errors="coerce"
    )

    pl["sales"] = pd.to_numeric(
        pl["sales"],
        errors="coerce"
    )

    revenue_cagr_rows = []

    for company_id, group in pl.groupby("company_id"):

        group = group.dropna(
            subset=["year", "sales"]
        ).sort_values("year")

        if len(group) < 2:
            continue

        latest = group.iloc[-1]

        target_year = latest["year"] - 5

        previous = group[
            group["year"] <= target_year
        ]

        if previous.empty:
            continue

        old = previous.iloc[-1]

        if (
            old["sales"] > 0
            and latest["sales"] > 0
            and latest["year"] > old["year"]
        ):
            years = latest["year"] - old["year"]

            cagr = (
                (latest["sales"] / old["sales"])
                ** (1 / years)
                - 1
            ) * 100

            revenue_cagr_rows.append(
                {
                    "company_id": company_id,
                    "revenue_cagr_5yr": cagr
                }
            )

    revenue_cagr = pd.DataFrame(
        revenue_cagr_rows
    )

    # -----------------------------------------------------
    # Latest financial ratios
    # -----------------------------------------------------
    if not ratios.empty:

        ratios["year"] = pd.to_numeric(
            ratios["year"],
            errors="coerce"
        )

        ratios = ratios.sort_values("year")

        latest_ratios = (
            ratios.groupby("company_id", as_index=False)
            .tail(1)
            .copy()
        )

    else:
        latest_ratios = pd.DataFrame()

    # -----------------------------------------------------
    # Find ROE column
    # -----------------------------------------------------
    roe_column = None

    for column in [
        "return_on_equity_pct",
        "roe",
        "roe_percentage"
    ]:
        if column in latest_ratios.columns:
            roe_column = column
            break

    if roe_column:

        latest_ratios["roe_value"] = pd.to_numeric(
            latest_ratios[roe_column],
            errors="coerce"
        )

        roe_data = latest_ratios[
            ["company_id", "roe_value"]
        ]

    else:

        roe_data = pd.DataFrame(
            columns=["company_id", "roe_value"]
        )

    # -----------------------------------------------------
    # Latest market cap
    # -----------------------------------------------------
    market_cap["year"] = pd.to_numeric(
        market_cap["year"],
        errors="coerce"
    )

    market_cap = market_cap.sort_values("year")

    latest_market_cap = (
        market_cap.groupby(
            "company_id",
            as_index=False
        )
        .tail(1)
        .copy()
    )

    latest_market_cap = latest_market_cap[
        ["company_id", "market_cap_crore"]
    ]

    # -----------------------------------------------------
    # Merge everything
    # -----------------------------------------------------
    df = companies.merge(
        sectors,
        on="company_id",
        how="left"
    )

    df = df.merge(
        latest_pl[
            ["company_id", "revenue"]
        ],
        on="company_id",
        how="left"
    )

    df = df.merge(
        revenue_cagr,
        on="company_id",
        how="left"
    )

    df = df.merge(
        roe_data,
        on="company_id",
        how="left"
    )

    df = df.merge(
        latest_market_cap,
        on="company_id",
        how="left"
    )

    df["sector"] = (
        df["sector"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    df["industry"] = (
        df["industry"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    return df


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
df = load_sector_data()

if df.empty:
    st.error("Sector data could not be loaded.")
    st.stop()


# ---------------------------------------------------------
# SECTOR SELECTOR
# ---------------------------------------------------------
sector_list = sorted(
    [
        sector
        for sector in df["sector"].unique()
        if sector and sector != "Unknown"
    ]
)

if not sector_list:
    st.warning("No sectors were found in the database.")
    st.stop()


selected_sector = st.selectbox(
    "Select Sector",
    sector_list
)


sector_df = df[
    df["sector"] == selected_sector
].copy()


# ---------------------------------------------------------
# KPI SECTION
# ---------------------------------------------------------
st.subheader(
    f"{selected_sector} — Sector Overview"
)

col1, col2, col3, col4 = st.columns(4)

median_roe = sector_df["roe_value"].median()
median_revenue_cagr = sector_df[
    "revenue_cagr_5yr"
].median()

median_revenue = sector_df[
    "revenue"
].median()

median_market_cap = sector_df[
    "market_cap_crore"
].median()


col1.metric(
    "Companies",
    len(sector_df)
)

col2.metric(
    "Median ROE",
    f"{median_roe:.2f}%"
    if pd.notna(median_roe)
    else "N/A"
)

col3.metric(
    "Median Revenue CAGR",
    f"{median_revenue_cagr:.2f}%"
    if pd.notna(median_revenue_cagr)
    else "N/A"
)

col4.metric(
    "Median Market Cap",
    f"₹{median_market_cap:,.0f} Cr"
    if pd.notna(median_market_cap)
    else "N/A"
)


st.divider()


# ---------------------------------------------------------
# BUBBLE CHART
# ---------------------------------------------------------
st.subheader("Revenue Growth vs ROE")

bubble_df = sector_df.dropna(
    subset=[
        "revenue_cagr_5yr",
        "roe_value"
    ]
).copy()


if bubble_df.empty:

    st.info(
        "There is not enough financial data to build the sector bubble chart."
    )

else:

    # Avoid zero/negative bubble sizes
    bubble_df["market_cap_size"] = (
        bubble_df["market_cap_crore"]
        .fillna(1)
        .clip(lower=1)
    )

    fig = px.scatter(
        bubble_df,
        x="revenue_cagr_5yr",
        y="roe_value",
        size="market_cap_size",
        color="industry",
        hover_name="company_name",
        hover_data={
            "company_id": True,
            "revenue_cagr_5yr": ":.2f",
            "roe_value": ":.2f",
            "market_cap_size": ":,.0f",
            "industry": True
        },
        labels={
            "revenue_cagr_5yr": "5-Year Revenue CAGR (%)",
            "roe_value": "ROE (%)",
            "market_cap_size": "Market Cap (₹ Cr)",
            "industry": "Sub-sector"
        },
        title=f"{selected_sector}: Revenue Growth vs ROE"
    )

    fig.update_layout(
        height=600,
        legend_title="Sub-sector"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ---------------------------------------------------------
# SECTOR MEDIAN KPI
# ---------------------------------------------------------
st.subheader("Sector Median KPI")

kpi_data = pd.DataFrame(
    {
        "Metric": [
            "ROE",
            "Revenue CAGR 5Y"
        ],
        "Median": [
            median_roe,
            median_revenue_cagr
        ]
    }
)

kpi_data = kpi_data.dropna(
    subset=["Median"]
)


if not kpi_data.empty:

    fig_kpi = px.bar(
        kpi_data,
        x="Metric",
        y="Median",
        text="Median",
        title=f"{selected_sector}: Median KPIs"
    )

    fig_kpi.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside"
    )

    fig_kpi.update_layout(
        height=400,
        yaxis_title="Value",
        xaxis_title=""
    )

    st.plotly_chart(
        fig_kpi,
        use_container_width=True
    )


# ---------------------------------------------------------
# COMPANY TABLE
# ---------------------------------------------------------
st.subheader(
    f"Companies in {selected_sector}"
)

display_df = sector_df[
    [
        "company_id",
        "company_name",
        "industry",
        "roe_value",
        "revenue_cagr_5yr",
        "revenue",
        "market_cap_crore"
    ]
].copy()

display_df = display_df.rename(
    columns={
        "company_id": "Ticker",
        "company_name": "Company",
        "industry": "Sub-sector",
        "roe_value": "ROE %",
        "revenue_cagr_5yr": "Revenue CAGR 5Y %",
        "revenue": "Revenue",
        "market_cap_crore": "Market Cap ₹ Cr"
    }
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)
