import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

# ------------------------------------------------------------------
# DATABASE PATH
# ------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"


# ------------------------------------------------------------------
# CONNECTION HELPER
# ------------------------------------------------------------------


def _get_connection():
    return sqlite3.connect(DB_PATH)


# ------------------------------------------------------------------
# COMPANIES
# ------------------------------------------------------------------


@st.cache_data(ttl=600)
def get_companies():
    """Return companies."""
    conn = _get_connection()

    query = """
        SELECT
            id,
            company_name,
            company_logo,
            chart_link,
            about_company,
            website,
            nse_profile,
            bse_profile,
            face_value,
            book_value,
            roce_percentage,
            roe_percentage
        FROM companies
        ORDER BY company_name
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


# ------------------------------------------------------------------
# FINANCIAL RATIOS
# ------------------------------------------------------------------


@st.cache_data(ttl=600)
def get_ratios(ticker, year=None):
    """Return ratios."""
    conn = _get_connection()

    query = """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
    """

    params = [ticker]

    if year is not None:
        query += " AND year = ?"
        params.append(int(year))

    query += " ORDER BY year"

    df = pd.read_sql_query(query, conn, params=params)

    conn.close()

    return df


# ------------------------------------------------------------------
# PROFIT & LOSS
# ------------------------------------------------------------------


@st.cache_data(ttl=600)
def get_pl(ticker):
    """Return pl."""
    conn = _get_connection()

    query = """
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year
    """

    df = pd.read_sql_query(query, conn, params=[ticker])

    conn.close()

    return df


# ------------------------------------------------------------------
# BALANCE SHEET
# ------------------------------------------------------------------


@st.cache_data(ttl=600)
def get_bs(ticker):
    """Return bs."""
    conn = _get_connection()

    query = """
        SELECT *
        FROM balancesheet
        WHERE company_id = ?
        ORDER BY year
    """

    df = pd.read_sql_query(query, conn, params=[ticker])

    conn.close()

    return df


# ------------------------------------------------------------------
# CASH FLOW
# ------------------------------------------------------------------


@st.cache_data(ttl=600)
def get_cf(ticker):
    """Return cf."""
    conn = _get_connection()

    query = """
        SELECT *
        FROM cashflow
        WHERE company_id = ?
        ORDER BY year
    """

    df = pd.read_sql_query(query, conn, params=[ticker])

    conn.close()

    return df


# ------------------------------------------------------------------
# SECTORS
# ------------------------------------------------------------------


@st.cache_data(ttl=600)
def get_sectors():
    """Return sectors."""
    conn = _get_connection()

    query = """
        SELECT
            s.company_id,
            c.company_name,
            s.sector,
            s.industry
        FROM sectors s
        LEFT JOIN companies c
            ON c.id = s.company_id
        ORDER BY s.sector, c.company_name
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


# ------------------------------------------------------------------
# PEER GROUPS
# ------------------------------------------------------------------


@st.cache_data(ttl=600)
def get_peers(group_name):
    """Return peers."""
    conn = _get_connection()

    query = """
        SELECT
            pg.company_id,
            c.company_name,
            pg.peer_group
        FROM peer_groups pg
        LEFT JOIN companies c
            ON c.id = pg.company_id
        WHERE pg.peer_group = ?
        ORDER BY c.company_name
    """

    df = pd.read_sql_query(query, conn, params=[group_name])

    conn.close()

    return df


# ------------------------------------------------------------------
# VALUATION
# ------------------------------------------------------------------


@st.cache_data(ttl=600)
def get_valuation(ticker):
    """Return valuation."""
    conn = _get_connection()

    query = """
        SELECT
            mc.company_id,
            c.company_name,
            mc.year,
            mc.market_cap_crore,
            mc.enterprise_value_crore,
            mc.pe_ratio,
            mc.pb_ratio,
            mc.ev_ebitda,
            mc.dividend_yield_pct
        FROM market_cap mc
        LEFT JOIN companies c
            ON c.id = mc.company_id
        WHERE mc.company_id = ?
        ORDER BY mc.year
    """

    df = pd.read_sql_query(query, conn, params=[ticker])

    conn.close()

    return df


# ------------------------------------------------------------------
# SUPPORTING HELPERS
# ------------------------------------------------------------------


@st.cache_data(ttl=600)
def get_company(ticker):
    """Return company."""
    companies = get_companies()

    result = companies[
        companies["id"].astype(str).str.upper() == str(ticker).upper()
    ].copy()

    return result


@st.cache_data(ttl=600)
def get_latest_ratios(ticker):
    """Return latest ratios."""
    ratios = get_ratios(ticker)

    if ratios.empty:
        return pd.DataFrame()

    return ratios.sort_values("year").tail(1).copy()


@st.cache_data(ttl=600)
def get_latest_valuation(ticker):
    """Return latest valuation."""
    valuation = get_valuation(ticker)

    if valuation.empty:
        return pd.DataFrame()

    return valuation.sort_values("year").tail(1).copy()


@st.cache_data(ttl=600)
def get_all_latest_ratios():
    """Return all latest ratios."""
    conn = _get_connection()

    query = """
        SELECT fr.*
        FROM financial_ratios fr
        INNER JOIN (
            SELECT company_id, MAX(year) AS latest_year
            FROM financial_ratios
            GROUP BY company_id
        ) latest
            ON fr.company_id = latest.company_id
           AND fr.year = latest.latest_year
        ORDER BY fr.company_id
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


@st.cache_data(ttl=600)
def get_all_latest_valuations():
    """Return all latest valuations."""
    conn = _get_connection()

    query = """
        SELECT mc.*
        FROM market_cap mc
        INNER JOIN (
            SELECT company_id, MAX(year) AS latest_year
            FROM market_cap
            GROUP BY company_id
        ) latest
            ON mc.company_id = latest.company_id
           AND mc.year = latest.latest_year
        ORDER BY mc.company_id
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


@st.cache_data(ttl=600)
def get_years():
    """Return years."""
    conn = _get_connection()

    query = """
        SELECT DISTINCT year
        FROM financial_ratios
        WHERE year IS NOT NULL
        ORDER BY year
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df["year"].astype(int).tolist()


@st.cache_data(ttl=600)
def get_peer_groups():
    """Return peer groups."""
    conn = _get_connection()

    query = """
        SELECT DISTINCT peer_group
        FROM peer_groups
        WHERE peer_group IS NOT NULL
          AND TRIM(peer_group) != ''
        ORDER BY peer_group
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df["peer_group"].tolist()


@st.cache_data(ttl=600)
def get_capital_allocation_data():
    """Return capital allocation data."""
    conn = _get_connection()

    tables = pd.read_sql_query(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        """,
        conn,
    )

    table_names = set(tables["name"].tolist())

    if "financial_ratios" not in table_names:
        conn.close()
        return pd.DataFrame()

    query = """
        SELECT
            fr.company_id,
            c.company_name,
            fr.year,
            fr.free_cash_flow_cr,
            fr.cash_from_operations_cr,
            fr.dividend_payout_ratio_pct,
            fr.debt_to_equity,
            fr.capex_intensity_pct
        FROM financial_ratios fr
        LEFT JOIN companies c
            ON c.id = fr.company_id
        INNER JOIN (
            SELECT company_id, MAX(year) AS latest_year
            FROM financial_ratios
            GROUP BY company_id
        ) latest
            ON fr.company_id = latest.company_id
           AND fr.year = latest.latest_year
        ORDER BY c.company_name
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df
