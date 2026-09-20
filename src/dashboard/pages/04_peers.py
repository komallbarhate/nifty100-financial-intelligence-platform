import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_peer_groups, get_peers
from src.screener.composite_score import CompositeScorer


st.set_page_config(
    page_title="Peer Comparison",
    page_icon="👥",
    layout="wide",
)

st.title("👥 Peer Comparison")
st.caption(
    "Compare a company against its assigned Nifty 100 peer group."
)


# =========================================================
# DATABASE PATH
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"


# =========================================================
# LOAD PEER PERCENTILES
# =========================================================

@st.cache_data(ttl=600)
def load_peer_percentiles():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query(
        """
        SELECT
            company_id,
            peer_group,
            metric,
            value,
            percentile_rank,
            year
        FROM peer_percentiles
        """,
        conn,
    )

    conn.close()

    return df


# =========================================================
# LOAD COMPANY MASTER
# =========================================================

@st.cache_data(ttl=600)
def load_companies():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query(
        """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        ORDER BY company_name
        """,
        conn,
    )

    conn.close()

    return df


# =========================================================
# LOAD COMPOSITE SCORES
# =========================================================

@st.cache_data(ttl=600)
def load_composite_scores():

    try:

        scorer = CompositeScorer()
        scores = scorer.calculate()

        if scores.empty:
            return pd.DataFrame(
                columns=[
                    "company_id",
                    "sprint3_composite_score",
                ]
            )

        required = [
            "company_id",
            "sprint3_composite_score",
        ]

        available = [
            column
            for column in required
            if column in scores.columns
        ]

        if len(available) < 2:
            return pd.DataFrame(
                columns=required
            )

        return scores[
            available
        ].copy()

    except Exception:
        return pd.DataFrame(
            columns=[
                "company_id",
                "sprint3_composite_score",
            ]
        )


# =========================================================
# LOAD DATA
# =========================================================

try:

    peer_groups = get_peer_groups()
    companies = load_companies()
    peer_percentiles = load_peer_percentiles()
    composite_scores = load_composite_scores()

except Exception as error:

    st.error(
        "Unable to load peer comparison data."
    )

    st.exception(error)

    st.stop()


if not peer_groups:

    st.warning(
        "No peer groups are available."
    )

    st.stop()


# =========================================================
# NORMALISE IDS
# =========================================================

for frame in [
    companies,
    peer_percentiles,
    composite_scores,
]:

    if (
        isinstance(frame, pd.DataFrame)
        and "company_id" in frame.columns
    ):

        frame["company_id"] = (
            frame["company_id"]
            .astype(str)
            .str.strip()
            .str.upper()
        )


# =========================================================
# PEER GROUP SELECTOR
# =========================================================

st.subheader("Peer Group")

selected_group = st.selectbox(
    "Select peer group",
    peer_groups,
)


# =========================================================
# LOAD GROUP MEMBERS
# =========================================================

group_members = get_peers(
    selected_group
).copy()


if group_members.empty:

    st.warning(
        f"No companies are assigned to {selected_group}."
    )

    st.stop()


# Normalise ID
group_members["company_id"] = (
    group_members["company_id"]
    .astype(str)
    .str.strip()
    .str.upper()
)


# =========================================================
# ENSURE COMPANY NAMES EXIST
# =========================================================

if "company_name" not in group_members.columns:

    group_members = group_members.merge(
        companies,
        on="company_id",
        how="left",
    )


# If the name column still doesn't exist,
# create a safe fallback.
if "company_name" not in group_members.columns:

    group_members["company_name"] = (
        group_members["company_id"]
    )


group_members = group_members.drop_duplicates(
    subset=["company_id"]
)

group_members = group_members.sort_values(
    "company_name"
)


# =========================================================
# COMPANY SELECTOR
# =========================================================

company_labels = {}

for _, row in group_members.iterrows():

    ticker = str(
        row["company_id"]
    )

    name = str(
        row["company_name"]
    )

    company_labels[
        f"{ticker} — {name}"
    ] = ticker


selected_label = st.selectbox(
    "Select company",
    list(company_labels.keys()),
)

selected_company = company_labels[
    selected_label
]


st.divider()


# =========================================================
# PEER PERCENTILE DATA
# =========================================================

group_percentiles = peer_percentiles[
    peer_percentiles["peer_group"]
    == selected_group
].copy()


if group_percentiles.empty:

    st.warning(
        "Peer percentile data is unavailable "
        "for this peer group."
    )

    st.stop()


# =========================================================
# RADAR METRICS
# =========================================================

radar_metrics = [
    ("ROE", "roe"),
    ("ROCE", "roce"),
    ("NPM", "npm"),
    ("D/E", "debt_to_equity"),
    ("FCF Score", "fcf"),
    ("PAT CAGR 5Y", "pat_cagr_5yr"),
    ("Revenue CAGR 5Y", "revenue_cagr_5yr"),
    ("Composite Score", "composite_score"),
]


# =========================================================
# PIVOT PERCENTILES
# =========================================================

pivot = (
    group_percentiles
    .pivot_table(
        index="company_id",
        columns="metric",
        values="percentile_rank",
        aggfunc="first",
    )
    .reset_index()
)


# =========================================================
# CONVERT PERCENTILES TO 0–100
# =========================================================

for _, metric in radar_metrics:

    if metric in pivot.columns:

        pivot[metric] = (
            pd.to_numeric(
                pivot[metric],
                errors="coerce",
            )
            * 100
        )


# =========================================================
# ADD COMPOSITE SCORE
# =========================================================

if not composite_scores.empty:

    pivot = pivot.merge(
        composite_scores[
            [
                "company_id",
                "sprint3_composite_score",
            ]
        ],
        on="company_id",
        how="left",
    )

    pivot["composite_score"] = pd.to_numeric(
        pivot["sprint3_composite_score"],
        errors="coerce",
    )

else:

    pivot["composite_score"] = np.nan


# =========================================================
# ADD COMPANY NAMES
# =========================================================

pivot = pivot.merge(
    companies,
    on="company_id",
    how="left",
)


if "company_name" not in pivot.columns:

    pivot["company_name"] = pivot[
        "company_id"
    ]


# =========================================================
# SELECTED COMPANY
# =========================================================

selected_rows = pivot[
    pivot["company_id"] == selected_company
].copy()


if selected_rows.empty:

    st.warning(
        "The selected company does not have "
        "peer percentile data."
    )

    st.stop()


selected_row = selected_rows.iloc[0]


# =========================================================
# PEER DATA
# =========================================================

peer_rows = pivot[
    pivot["company_id"] != selected_company
].copy()


if peer_rows.empty:

    peer_rows = pivot.copy()


# =========================================================
# RADAR SECTION
# =========================================================

st.subheader(
    f"{selected_company} vs {selected_group}"
)

radar_col, summary_col = st.columns(
    [1.5, 1]
)


# =========================================================
# RADAR CHART
# =========================================================

with radar_col:

    labels = [
        label
        for label, _ in radar_metrics
    ]

    metric_names = [
        metric
        for _, metric in radar_metrics
    ]

    company_values = []
    peer_values = []

    for metric in metric_names:

        company_value = selected_row.get(
            metric,
            np.nan,
        )

        if metric in peer_rows.columns:

            peer_series = pd.to_numeric(
                peer_rows[metric],
                errors="coerce",
            ).dropna()

        else:

            peer_series = pd.Series(
                dtype=float
            )


        if pd.isna(company_value):

            company_value = 50.0


        if peer_series.empty:

            peer_average = 50.0

        else:

            peer_average = float(
                peer_series.mean()
            )


        company_values.append(
            float(company_value)
        )

        peer_values.append(
            peer_average
        )


    fig = go.Figure()


    fig.add_trace(
        go.Scatterpolar(
            r=company_values + [
                company_values[0]
            ],
            theta=labels + [
                labels[0]
            ],
            fill="toself",
            name=selected_company,
        )
    )


    fig.add_trace(
        go.Scatterpolar(
            r=peer_values + [
                peer_values[0]
            ],
            theta=labels + [
                labels[0]
            ],
            fill="toself",
            name="Peer Average",
            line=dict(
                dash="dash"
            ),
        )
    )


    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
            )
        ),
        showlegend=True,
        height=600,
        margin=dict(
            l=40,
            r=40,
            t=60,
            b=40,
        ),
    )


    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# =========================================================
# SUMMARY
# =========================================================

with summary_col:

    st.markdown("### Selected Company")

    st.metric(
        "Peer Group",
        selected_group,
    )

    st.metric(
        "Companies in Peer Group",
        len(pivot),
    )


    st.markdown(
        "### Percentile Comparison"
    )


    comparison_rows = []


    for label, metric in radar_metrics:

        company_value = selected_row.get(
            metric,
            np.nan,
        )


        if metric in peer_rows.columns:

            peer_series = pd.to_numeric(
                peer_rows[metric],
                errors="coerce",
            ).dropna()

        else:

            peer_series = pd.Series(
                dtype=float
            )


        if peer_series.empty:

            peer_average = np.nan

        else:

            peer_average = peer_series.mean()


        comparison_rows.append(
            {
                "Metric": label,
                "Company": company_value,
                "Peer Average": peer_average,
            }
        )


    comparison_df = pd.DataFrame(
        comparison_rows
    )


    st.dataframe(
        comparison_df.style.format(
            {
                "Company": "{:.1f}",
                "Peer Average": "{:.1f}",
            },
            na_rep="N/A",
        ),
        use_container_width=True,
        hide_index=True,
    )


st.divider()


# =========================================================
# SIDE-BY-SIDE PEER TABLE
# =========================================================

st.subheader(
    f"Peer Companies — {selected_group}"
)


table_rows = []


for _, row in pivot.iterrows():

    ticker = str(
        row["company_id"]
    )

    name = row.get(
        "company_name",
        ticker,
    )


    table_rows.append(
        {
            "Ticker": ticker,
            "Company": name,
            "ROE": row.get(
                "roe",
                np.nan,
            ),
            "ROCE": row.get(
                "roce",
                np.nan,
            ),
            "NPM": row.get(
                "npm",
                np.nan,
            ),
            "D/E Percentile": row.get(
                "debt_to_equity",
                np.nan,
            ),
            "FCF Score": row.get(
                "fcf",
                np.nan,
            ),
            "PAT CAGR 5Y": row.get(
                "pat_cagr_5yr",
                np.nan,
            ),
            "Revenue CAGR 5Y": row.get(
                "revenue_cagr_5yr",
                np.nan,
            ),
            "Composite Score": row.get(
                "composite_score",
                np.nan,
            ),
        }
    )


comparison_table = pd.DataFrame(
    table_rows
)


if "Composite Score" in comparison_table.columns:

    comparison_table = comparison_table.sort_values(
        "Composite Score",
        ascending=False,
        na_position="last",
    )


# =========================================================
# HIGHLIGHT SELECTED COMPANY
# =========================================================

def highlight_selected(row):

    if row["Ticker"] == selected_company:

        return [
            "font-weight: bold"
            for _ in row
        ]

    return [
        ""
        for _ in row
    ]


st.dataframe(
    comparison_table.style
    .apply(
        highlight_selected,
        axis=1,
    )
    .format(
        {
            "ROE": "{:.1f}",
            "ROCE": "{:.1f}",
            "NPM": "{:.1f}",
            "D/E Percentile": "{:.1f}",
            "FCF Score": "{:.1f}",
            "PAT CAGR 5Y": "{:.1f}",
            "Revenue CAGR 5Y": "{:.1f}",
            "Composite Score": "{:.1f}",
        },
        na_rep="N/A",
    ),
    use_container_width=True,
    hide_index=True,
)


st.caption(
    "Radar values are peer percentiles on a 0–100 scale. "
    "For D/E, a higher percentile represents lower relative leverage."
)
