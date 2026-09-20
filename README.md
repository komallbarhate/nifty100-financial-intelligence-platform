# NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM

A comprehensive financial analytics platform for the NIFTY 100 universe, built with Python, Pandas, SQLite, FastAPI, Streamlit and Plotly.

The platform combines financial data ingestion, data-quality validation, KPI calculation, financial screening, peer comparison, valuation analysis, cash-flow intelligence, clustering, REST APIs and an interactive dashboard.

---

## 1. Project Overview

The NIFTY 100 Financial Intelligence Platform transforms structured financial datasets into an integrated analytics system for company-level and portfolio-level analysis.

The platform provides:

- Financial data ingestion and normalization
- SQLite-based analytical database
- Data-quality validation
- Financial ratio calculation
- CAGR analysis
- Cash-flow intelligence
- Capital allocation analysis
- Financial screening
- Peer comparison
- Valuation analysis
- KMeans company clustering
- Portfolio-level statistics
- Annual report/document access
- Company tearsheet reports
- Sector reports
- FastAPI REST API
- Streamlit analytical dashboard
- Automated pytest validation

---

## 2. Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Data Processing | Pandas, NumPy |
| Database | SQLite |
| Data Visualization | Plotly, Matplotlib, Seaborn |
| Dashboard | Streamlit |
| API | FastAPI |
| API Server | Uvicorn |
| Machine Learning | Scikit-learn |
| Testing | Pytest |
| API Testing | FastAPI TestClient |
| Reports | ReportLab |
| Data Sources | Excel/CSV financial datasets |

---

## 3. Project Structure

```text
nifty100-project/
│
├── config/
│   └── .env.template
│
├── data/
│   ├── raw/
│   ├── supporting/
│   └── nifty100.db
│
├── docs/
│
├── notebooks/
│
├── output/
│
├── reports/
│   ├── portfolio/
│   ├── sector/
│   ├── tearsheets/
│   ├── elbow_plot.png
│   ├── correlation_heatmap.png
│   ├── openapi.json
│   ├── postman_collection.json
│   └── pytest_report_day42.html
│
├── src/
│   ├── analytics/
│   ├── api/
│   │   ├── main.py
│   │   └── routers/
│   ├── dashboard/
│   │   ├── app.py
│   │   └── pages/
│   ├── etl/
│   ├── nlp/
│   ├── performance/
│   └── reports/
│
├── tests/
│   ├── etl/
│   ├── kpi/
│   ├── test_api.py
│   ├── test_integration.py
│   ├── test_dashboard.py
│   └── test_performance.py
│
├── requirements.txt
└── README.md