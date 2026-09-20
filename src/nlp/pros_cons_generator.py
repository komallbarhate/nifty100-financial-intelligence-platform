from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

OUTPUT_PATH = OUTPUT_DIR / "pros_cons_generated.csv"


# ============================================================
# HELPERS
# ============================================================

def numeric(series):
    return pd.to_numeric(series, errors="coerce")


def company_rows(df, company_id):
    if df.empty or "company_id" not in df.columns:
        return pd.DataFrame()

    rows = df[
        df["company_id"].astype(str).str.strip()
        == str(company_id).strip()
    ].copy()

    if "year" in rows.columns:
        rows["year"] = numeric(rows["year"])
        rows = rows.sort_values("year")

    return rows


def series_for(df, company_id, column):
    if column is None:
        return pd.Series(dtype=float)

    rows = company_rows(df, company_id)

    if rows.empty or column not in rows.columns:
        return pd.Series(dtype=float)

    return numeric(rows[column]).dropna()


def latest(series):
    if series.empty:
        return np.nan

    return float(series.iloc[-1])


def consecutive_positive(series, years):
    if len(series) < years:
        return False

    return bool((series.tail(years) > 0).all())


def consecutive_negative(series, years):
    if len(series) < years:
        return False

    return bool((series.tail(years) < 0).all())


def increasing(series, years):
    if len(series) < years:
        return False

    values = series.tail(years).tolist()

    return all(
        values[i] > values[i - 1]
        for i in range(1, len(values))
    )


def decreasing(series, years):
    if len(series) < years:
        return False

    values = series.tail(years).tolist()

    return all(
        values[i] < values[i - 1]
        for i in range(1, len(values))
    )


def above(series, threshold, years):
    if len(series) < years:
        return False

    return bool(
        (series.tail(years) > threshold).all()
    )


def load_table(conn, table):
    try:
        return pd.read_sql_query(
            f"SELECT * FROM {table}",
            conn
        )
    except Exception:
        return pd.DataFrame()


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("NIFTY 100 AUTO PROS / CONS GENERATOR")
    print("=" * 70)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(DB_PATH)

    companies = load_table(
        conn,
        "companies"
    )

    ratios = load_table(
        conn,
        "financial_ratios"
    )

    pl = load_table(
        conn,
        "profitandloss"
    )

    bs = load_table(
        conn,
        "balancesheet"
    )

    cf = load_table(
        conn,
        "cashflow"
    )

    sectors = load_table(
        conn,
        "sectors"
    )

    conn.close()

    print(f"\nCompanies : {len(companies)}")
    print(f"Ratios    : {len(ratios)} rows")
    print(f"P&L       : {len(pl)} rows")
    print(f"Balance   : {len(bs)} rows")
    print(f"Cash Flow : {len(cf)} rows")

    # ========================================================
    # EXACT DATABASE COLUMNS
    # ========================================================

    roe_col = "return_on_equity_pct"
    roce_col = "return_on_capital_employed_pct"
    de_col = "debt_to_equity"
    opm_col = "operating_profit_margin_pct"

    revenue_cagr_col = "revenue_cagr_5yr"
    pat_cagr_col = "pat_cagr_5yr"
    eps_cagr_col = "eps_cagr_5yr"

    fcf_col = "free_cash_flow_cr"
    icr_col = "interest_coverage"

    payout_col = "dividend_payout_ratio_pct"

    net_debt_col = "net_debt"

    revenue_col = "sales"
    net_profit_col = "net_profit"
    eps_col = "eps"

    assets_col = "total_assets"
    debt_col = "borrowings"

    print("\nUsing exact database columns:")

    print(f"  ROE             : {roe_col}")
    print(f"  ROCE            : {roce_col}")
    print(f"  D/E             : {de_col}")
    print(f"  OPM             : {opm_col}")
    print(f"  Revenue CAGR    : {revenue_cagr_col}")
    print(f"  PAT CAGR        : {pat_cagr_col}")
    print(f"  EPS CAGR        : {eps_cagr_col}")
    print(f"  FCF             : {fcf_col}")
    print(f"  ICR             : {icr_col}")
    print(f"  Dividend Payout : {payout_col}")
    print(f"  Net Debt        : {net_debt_col}")

    print("\nP&L:")
    print(f"  Revenue         : {revenue_col}")
    print(f"  Net Profit      : {net_profit_col}")
    print(f"  EPS             : {eps_col}")

    print("\nBalance Sheet:")
    print(f"  Assets          : {assets_col}")
    print(f"  Debt            : {debt_col}")

    # ========================================================
    # SECTOR MAPPING
    # ========================================================

    sector_map = {}

    if not sectors.empty:

        sector_rows = sectors[
            ["company_id", "sector"]
        ].drop_duplicates(
            "company_id"
        )

        sector_map = dict(
            zip(
                sector_rows["company_id"].astype(str),
                sector_rows["sector"].fillna("").astype(str)
            )
        )

    # Financial-sector keywords.
    # CON-01 specifically applies to non-financial companies.
    financial_keywords = [
        "bank",
        "financial",
        "insurance",
        "finance",
        "nbfc",
        "housing finance",
        "capital market",
        "asset management",
        "investment",
    ]

    def is_financial(company_id):

        sector = sector_map.get(
            str(company_id),
            ""
        ).lower()

        return any(
            keyword in sector
            for keyword in financial_keywords
        )

    # ========================================================
    # COMPANY IDS
    # ========================================================

    company_ids = (
        companies["id"]
        .astype(str)
        .str.strip()
        .unique()
    )

    records = []

    # ========================================================
    # PROCESS EVERY COMPANY
    # ========================================================

    for company_id in company_ids:

        roe = series_for(
            ratios,
            company_id,
            roe_col
        )

        roce = series_for(
            ratios,
            company_id,
            roce_col
        )

        de = series_for(
            ratios,
            company_id,
            de_col
        )

        opm = series_for(
            ratios,
            company_id,
            opm_col
        )

        revenue_cagr = series_for(
            ratios,
            company_id,
            revenue_cagr_col
        )

        pat_cagr = series_for(
            ratios,
            company_id,
            pat_cagr_col
        )

        eps_cagr = series_for(
            ratios,
            company_id,
            eps_cagr_col
        )

        fcf = series_for(
            ratios,
            company_id,
            fcf_col
        )

        icr = series_for(
            ratios,
            company_id,
            icr_col
        )

        payout = series_for(
            ratios,
            company_id,
            payout_col
        )

        net_debt = series_for(
            ratios,
            company_id,
            net_debt_col
        )

        revenue = series_for(
            pl,
            company_id,
            revenue_col
        )

        net_profit = series_for(
            pl,
            company_id,
            net_profit_col
        )

        eps = series_for(
            pl,
            company_id,
            eps_col
        )

        assets = series_for(
            bs,
            company_id,
            assets_col
        )

        debt = series_for(
            bs,
            company_id,
            debt_col
        )

        latest_roe = latest(roe)
        latest_roce = latest(roce)
        latest_de = latest(de)
        latest_opm = latest(opm)
        latest_revenue_cagr = latest(revenue_cagr)
        latest_pat_cagr = latest(pat_cagr)
        latest_eps_cagr = latest(eps_cagr)
        latest_fcf = latest(fcf)
        latest_icr = latest(icr)
        latest_payout = latest(payout)
        latest_net_profit = latest(net_profit)
        latest_net_debt = latest(net_debt)

        # ====================================================
        # PRO RULES
        # ====================================================

        # PRO-01
        if above(roe, 20, 3):
            records.append({
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO-01",
                "text": (
                    "Consistently high return on equity "
                    "above 20% demonstrates exceptional "
                    "capital efficiency"
                ),
                "confidence_pct": 90,
            })

        # PRO-02
        if consecutive_positive(fcf, 5):
            records.append({
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO-02",
                "text": (
                    "Strong free cash flow generation "
                    "over 5 years signals healthy "
                    "business fundamentals"
                ),
                "confidence_pct": 90,
            })

        # PRO-03
        if not pd.isna(latest_de) and latest_de == 0:
            records.append({
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO-03",
                "text": (
                    "Debt-free balance sheet provides "
                    "financial flexibility and eliminates "
                    "interest burden"
                ),
                "confidence_pct": 95,
            })

        # PRO-04
        if (
            not pd.isna(latest_revenue_cagr)
            and latest_revenue_cagr > 15
        ):
            records.append({
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO-04",
                "text": (
                    "Revenue growing at above 15% CAGR "
                    "over 5 years reflects strong "
                    "business momentum"
                ),
                "confidence_pct": 90,
            })

        # PRO-05
        if (
            not pd.isna(latest_opm)
            and latest_opm > 25
        ):
            records.append({
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO-05",
                "text": (
                    "Operating profit margin above 25% "
                    "indicates strong pricing power "
                    "and cost discipline"
                ),
                "confidence_pct": 88,
            })

        # PRO-06
        if (
            not pd.isna(latest_pat_cagr)
            and latest_pat_cagr > 20
        ):
            records.append({
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO-06",
                "text": (
                    "Net profit compounding at above "
                    "20% over 5 years creates significant "
                    "shareholder value"
                ),
                "confidence_pct": 90,
            })

        # PRO-07
        if (
            (
                not pd.isna(latest_icr)
                and latest_icr > 10
            )
            or (
                not pd.isna(latest_de)
                and latest_de == 0
            )
        ):
            records.append({
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO-07",
                "text": (
                    "Very high interest coverage ratio "
                    "reflects negligible financial stress "
                    "from debt servicing"
                ),
                "confidence_pct": 92,
            })

        # PRO-08
        # Dividend yield is NOT present in the database,
        # therefore this rule cannot be evaluated.
        # We deliberately do not fabricate it.

        # PRO-09
        if (
            not pd.isna(latest_eps_cagr)
            and latest_eps_cagr > 15
        ):
            records.append({
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO-09",
                "text": (
                    "Earnings per share growing above "
                    "15% CAGR indicates strong earnings "
                    "quality and compounding"
                ),
                "confidence_pct": 88,
            })

        # PRO-10
        if increasing(roe, 3):
            records.append({
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO-10",
                "text": (
                    "Return on equity improving for "
                    "3 consecutive years shows "
                    "strengthening business quality"
                ),
                "confidence_pct": 82,
            })

        # PRO-11
        if (
            not pd.isna(latest_revenue_cagr)
            and not pd.isna(latest_pat_cagr)
            and latest_revenue_cagr < latest_pat_cagr
        ):
            records.append({
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO-11",
                "text": (
                    "Revenue growing slower than profits "
                    "shows improving operating leverage "
                    "and scale benefits"
                ),
                "confidence_pct": 78,
            })

        # PRO-12
        if (
            increasing(assets, 3)
            and decreasing(debt, 3)
        ):
            records.append({
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO-12",
                "text": (
                    "Growing asset base funded by internal "
                    "accruals reflects self-sustaining growth"
                ),
                "confidence_pct": 84,
            })

        # ====================================================
        # CON RULES
        # ====================================================

        # CON-01
        if (
            not is_financial(company_id)
            and not pd.isna(latest_de)
            and latest_de > 2
        ):
            records.append({
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON-01",
                "text": (
                    f"Debt-to-equity ratio of "
                    f"{latest_de:.2f} is elevated for "
                    "a non-financial company and warrants "
                    "monitoring"
                ),
                "confidence_pct": 90,
            })

        # CON-02
        if consecutive_negative(fcf, 3):
            records.append({
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON-02",
                "text": (
                    "Free cash flow negative for "
                    "3 consecutive years raises concern "
                    "about cash generation quality"
                ),
                "confidence_pct": 92,
            })

        # CON-03
        if decreasing(opm, 3):
            records.append({
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON-03",
                "text": (
                    "Operating margins declining for "
                    "3 consecutive years suggest pricing "
                    "or cost pressure"
                ),
                "confidence_pct": 85,
            })

        # CON-04
        if (
            not pd.isna(latest_net_profit)
            and latest_net_profit < 0
        ):
            records.append({
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON-04",
                "text": (
                    "Company reported a net loss in "
                    "the most recent financial year"
                ),
                "confidence_pct": 98,
            })

        # CON-05
        if decreasing(revenue, 2):
            records.append({
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON-05",
                "text": (
                    "Revenue contraction over "
                    "2 consecutive years indicates "
                    "demand weakness or market share loss"
                ),
                "confidence_pct": 88,
            })

        # CON-06
        if (
            not pd.isna(latest_icr)
            and latest_icr < 1.5
        ):
            records.append({
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON-06",
                "text": (
                    "Interest coverage ratio below 1.5x "
                    "indicates the company is at risk "
                    "of not meeting its debt obligations"
                ),
                "confidence_pct": 94,
            })

        # CON-07
        if (
            not pd.isna(latest_payout)
            and latest_payout > 100
        ):
            records.append({
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON-07",
                "text": (
                    "Dividend payout ratio above 100% "
                    "means the company is paying dividends "
                    "from reserves, which is unsustainable"
                ),
                "confidence_pct": 92,
            })

        # CON-08
        if increasing(de, 3):
            records.append({
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON-08",
                "text": (
                    "Rising debt-to-equity ratio over "
                    "3 years suggests increasing "
                    "financial leverage risk"
                ),
                "confidence_pct": 88,
            })

        # CON-09
        if decreasing(eps, 3):
            records.append({
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON-09",
                "text": (
                    "Earnings per share declining for "
                    "3 consecutive years reflects "
                    "deteriorating profitability"
                ),
                "confidence_pct": 90,
            })

        # CON-10
        if (
            not pd.isna(latest_roce)
            and latest_roce < 10
        ):
            records.append({
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON-10",
                "text": (
                    "Return on capital employed below "
                    "10% suggests the business is not "
                    "generating sufficient returns on "
                    "invested capital"
                ),
                "confidence_pct": 86,
            })

        # CON-11
        # EBITDA is not present in the database schema,
        # so this rule cannot be evaluated.
        # We deliberately do not substitute another metric.

        # CON-12
        if (
            not pd.isna(latest_revenue_cagr)
            and latest_revenue_cagr < 5
        ):
            records.append({
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON-12",
                "text": (
                    "Revenue growing at below 5% over "
                    "5 years lags inflation and suggests "
                    "limited business momentum"
                ),
                "confidence_pct": 85,
            })

    # ========================================================
    # DATAFRAME
    # ========================================================

    output = pd.DataFrame(
        records,
        columns=[
            "company_id",
            "type",
            "rule_id",
            "text",
            "confidence_pct",
        ]
    )

    if not output.empty:

        output = output[
            output["confidence_pct"] > 60
        ].copy()

        output = output.sort_values(
            [
                "company_id",
                "type",
                "rule_id",
            ]
        ).reset_index(drop=True)

    output.to_csv(
        OUTPUT_PATH,
        index=False
    )

    # ========================================================
    # COVERAGE
    # ========================================================

    company_set = set(
        company_ids
    )

    pro_companies = set(
        output.loc[
            output["type"] == "pro",
            "company_id"
        ]
    ) if not output.empty else set()

    con_companies = set(
        output.loc[
            output["type"] == "con",
            "company_id"
        ]
    ) if not output.empty else set()

    missing_pro = sorted(
        company_set - pro_companies
    )

    missing_con = sorted(
        company_set - con_companies
    )

    # ========================================================
    # REPORT
    # ========================================================

    print("\n" + "=" * 70)
    print("PROS / CONS OUTPUT")
    print("=" * 70)

    print(
        f"Total records       : {len(output)}"
    )

    print(
        f"Pro records         : "
        f"{(output['type'] == 'pro').sum() if not output.empty else 0}"
    )

    print(
        f"Con records         : "
        f"{(output['type'] == 'con').sum() if not output.empty else 0}"
    )

    print(
        f"Companies           : {len(company_set)}"
    )

    print(
        f"Companies with pro  : {len(pro_companies)}"
    )

    print(
        f"Companies with con  : {len(con_companies)}"
    )

    print(
        f"Missing pro         : {len(missing_pro)}"
    )

    print(
        f"Missing con         : {len(missing_con)}"
    )

    if missing_pro:

        print("\nCompanies missing pro:")
        print(
            ", ".join(missing_pro)
        )

    if missing_con:

        print("\nCompanies missing con:")
        print(
            ", ".join(missing_con)
        )

    print("\nRule distribution:")

    if not output.empty:

        print(
            output[
                "rule_id"
            ]
            .value_counts()
            .sort_index()
            .to_string()
        )

    print("\nOutput:")
    print(OUTPUT_PATH)

    print("\nGENERATOR COMPLETE")


if __name__ == "__main__":
    main()