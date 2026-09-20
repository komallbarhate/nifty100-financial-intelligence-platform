import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard.utils.db import get_companies

st.set_page_config(
    page_title="Annual Reports | Nifty 100 Analytics", page_icon="R", layout="wide"
)

st.title("Annual Reports")
st.caption("Access annual reports and company filings from BSE.")


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"


@st.cache_data(ttl=600)
def get_documents():
    """Return documents."""
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            d.company_id,
            d.year,
            d.document,
            c.company_name
        FROM documents d
        LEFT JOIN companies c
            ON c.id = d.company_id
        ORDER BY c.company_name, d.year DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


companies = get_companies()
documents = get_documents()

if companies.empty:
    st.error("Company data could not be loaded.")
    st.stop()

if documents.empty:
    st.warning("No annual report records were found.")
    st.stop()


company_map = (
    companies[["id", "company_name"]]
    .dropna()
    .drop_duplicates()
    .sort_values("company_name")
)

company_options = company_map["id"].tolist()

default_company = (
    "ADANIPORTS" if "ADANIPORTS" in company_options else company_options[0]
)

selected_company = st.selectbox(
    "Search company",
    company_options,
    index=company_options.index(default_company),
    format_func=lambda x: (
        f"{x} — " f"{company_map.loc[company_map['id'] == x, 'company_name'].iloc[0]}"
    ),
)


company_info = company_map[company_map["id"] == selected_company]

company_name = (
    company_info["company_name"].iloc[0] if not company_info.empty else selected_company
)

st.subheader(company_name)
st.caption(f"NSE Ticker: {selected_company}")


company_reports = documents[
    documents["company_id"].astype(str).str.upper() == selected_company.upper()
].copy()

if company_reports.empty:
    st.warning("No annual report records found for this company.")
    st.stop()


company_reports["year"] = pd.to_numeric(company_reports["year"], errors="coerce")

company_reports = company_reports.dropna(subset=["year"])

company_reports["year"] = company_reports["year"].astype(int)

available_years = sorted(company_reports["year"].unique(), reverse=True)


selected_years = st.multiselect(
    "Filter report years", options=available_years, default=available_years[:1]
)

if not selected_years:
    st.info("Select at least one report year.")
    st.stop()


filtered_reports = company_reports[
    company_reports["year"].isin(selected_years)
].sort_values("year", ascending=False)


st.divider()

st.subheader("Available Annual Reports")


for _, row in filtered_reports.iterrows():

    year = int(row["year"])

    document_url = row["document"]

    if pd.isna(document_url):
        document_url = ""

    document_url = str(document_url).strip()

    st.markdown(f"### Annual Report {year}")

    if document_url:

        st.success("BSE annual report PDF link available.")

        st.markdown(
            f"""
            <a href="{document_url}" target="_blank"
               style="
               display:block;
               text-align:center;
               padding:10px;
               border:1px solid #555;
               border-radius:6px;
               text-decoration:none;
               color:white;
               background:#111827;
               font-weight:600;
               ">
               Open BSE Annual Report {year}
            </a>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.error("Report unavailable — no BSE PDF link is stored for this year.")

    st.divider()


st.subheader("Report Records")

table = filtered_reports[["company_id", "year", "document"]].copy()

table["Status"] = table["document"].apply(
    lambda x: ("Available" if pd.notna(x) and str(x).strip() else "Unavailable")
)

table["Document URL"] = table["document"].fillna("")

table = table[["company_id", "year", "Status", "Document URL"]]

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Document URL": st.column_config.LinkColumn(
            "Document URL", display_text="Open PDF"
        )
    },
)

st.caption(
    "Report links are sourced from the BSE annual-report URLs "
    "provided in the project documents dataset."
)
