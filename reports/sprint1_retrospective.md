# NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM

# Sprint 1 Retrospective — Data Foundation

**Sprint:** Day 01–07  
**Epic:** EPIC 01 — Data Ingestion & ETL  
**Sprint Due:** 22 September 2026

---

## 1. Sprint Objective

The objective of Sprint 1 was to establish a reliable data foundation for the NIFTY 100 Financial Intelligence Platform.

The sprint focused on:

- Project environment setup
- Excel data ingestion
- Data normalization
- Data quality validation
- SQLite database design
- ETL loading
- Referential integrity validation
- Manual data review
- Exploratory SQL analysis

---

# 2. Source Data

The project uses the following source datasets.

## Core datasets

1. analysis
2. balancesheet
3. cashflow
4. companies
5. documents
6. profitandloss
7. prosandcons

## Supporting datasets

8. financial_ratios
9. market_cap
10. peer_groups
11. sectors
12. stock_prices

The source company master contains **92 companies**.

---

# 3. Day 01 — Environment Setup

Completed:

- Project directory structure created
- Python virtual environment created
- Required dependencies installed
- `.env` configuration created
- `requirements.txt` generated
- ETL source directories created
- Database and output directories created

Python environment used:

```text
.venv