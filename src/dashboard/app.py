import streamlit as st


st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.title("Nifty 100 Analytics")
st.markdown(
    """
    ### Financial Intelligence Platform

    Explore Nifty 100 companies through financial ratios, screening,
    peer comparison, trends, sector analysis, capital allocation,
    annual reports, and valuation.
    """
)


st.sidebar.title("Navigation")
st.sidebar.caption("Nifty 100 Financial Intelligence Platform")

st.sidebar.info(
    """
    Use the page navigation above to explore the dashboard.

    **Coverage**
    - 92 Nifty 100 companies
    - Financial ratios
    - Screener presets
    - Peer analysis
    - Historical trends
    - Sector analytics
    - Capital allocation
    - Annual reports
    - Valuation
    """
)


st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Companies", "92")

with col2:
    st.metric("Financial Years", "2011–2024")

with col3:
    st.metric("Peer Groups", "11")


st.success(
    "Dashboard scaffold loaded successfully. "
    "Use the pages in the sidebar to explore the platform."
)
