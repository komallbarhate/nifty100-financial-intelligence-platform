import csv
import math
import sqlite3
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    # ruff: noqa: E402

from src.analytics.cagr import calculate_window_cagr
from src.analytics.cashflow_kpis import (
    capex_intensity,
    capital_allocation_pattern,
    cfo_pat_ratio,
    classify_capex_intensity,
    classify_cfo_quality,
    fcf_conversion_rate,
    free_cash_flow,
    sign,
)
from src.analytics.ratios import (
    asset_turnover,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_label,
    interest_coverage_ratio,
    interest_coverage_warning,
    net_debt,
    net_profit_margin,
    operating_profit_margin,
    return_on_assets,
    return_on_capital_employed,
    return_on_equity,
)

DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

CAPITAL_ALLOCATION_FILE = (
    OUTPUT_DIR / "capital_allocation.csv"
)

EDGE_CASE_LOG = (
    OUTPUT_DIR / "ratio_edge_cases.log"
)


def safe_float(value) -> Optional[float]:

    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(value) or math.isinf(value):
        return None

    return value


def calculate_book_value_per_share(
    book_value,
    face_value,
):

    book_value = safe_float(book_value)
    face_value = safe_float(face_value)

    if book_value is None:
        return None

    if face_value is None or face_value <= 0:
        return None

    return book_value


def calculate_composite_quality_score(
    roe,
    roce,
    debt_equity,
    interest_coverage,
    revenue_cagr,
    pat_cagr,
):

    scores = []

    if roe is not None:

        if roe >= 20:
            scores.append(100)
        elif roe >= 15:
            scores.append(80)
        elif roe >= 10:
            scores.append(60)
        elif roe >= 5:
            scores.append(40)
        else:
            scores.append(20)

    if roce is not None:

        if roce >= 20:
            scores.append(100)
        elif roce >= 15:
            scores.append(80)
        elif roce >= 10:
            scores.append(60)
        elif roce >= 5:
            scores.append(40)
        else:
            scores.append(20)

    if debt_equity is not None:

        if debt_equity <= 0.5:
            scores.append(100)
        elif debt_equity <= 1:
            scores.append(80)
        elif debt_equity <= 2:
            scores.append(60)
        elif debt_equity <= 5:
            scores.append(40)
        else:
            scores.append(20)

    if interest_coverage is not None:

        if interest_coverage >= 5:
            scores.append(100)
        elif interest_coverage >= 3:
            scores.append(80)
        elif interest_coverage >= 1.5:
            scores.append(60)
        else:
            scores.append(20)

    for growth in (
        revenue_cagr,
        pat_cagr,
    ):

        if growth is not None:

            if growth >= 15:
                scores.append(100)
            elif growth >= 10:
                scores.append(80)
            elif growth >= 5:
                scores.append(60)
            elif growth >= 0:
                scores.append(40)
            else:
                scores.append(20)

    if not scores:
        return None

    return sum(scores) / len(scores)


def get_sector_map(conn):

    rows = conn.execute(
        """
        SELECT
            company_id,
            sector,
            industry
        FROM sectors
        """
    ).fetchall()

    result = {}

    for company_id, sector, industry in rows:

        result[company_id] = {
            "sector": sector,
            "industry": industry,
        }

    return result


def get_source_company_data(conn):

    rows = conn.execute(
        """
        SELECT
            id,
            company_name,
            face_value,
            book_value,
            roce_percentage,
            roe_percentage
        FROM companies
        """
    ).fetchall()

    result = {}

    for row in rows:

        result[row[0]] = {
            "company_name": row[1],
            "face_value": safe_float(row[2]),
            "book_value": safe_float(row[3]),
            "source_roce": safe_float(row[4]),
            "source_roe": safe_float(row[5]),
        }

    return result


def get_financial_data(conn):

    pnl_rows = conn.execute(
        """
        SELECT
            company_id,
            year,
            sales,
            operating_profit,
            opm_percentage,
            other_income,
            interest,
            net_profit,
            eps,
            dividend_payout
        FROM profitandloss
        WHERE company_id IS NOT NULL
          AND year IS NOT NULL
        ORDER BY company_id, year
        """
    ).fetchall()

    bs_rows = conn.execute(
        """
        SELECT
            company_id,
            year,
            share_capital,
            reserves,
            borrowings,
            investments,
            total_assets
        FROM balancesheet
        WHERE company_id IS NOT NULL
          AND year IS NOT NULL
        ORDER BY company_id, year
        """
    ).fetchall()

    cf_rows = conn.execute(
        """
        SELECT
            company_id,
            year,
            operating_activity,
            investing_activity,
            financing_activity
        FROM cashflow
        WHERE company_id IS NOT NULL
          AND year IS NOT NULL
        ORDER BY company_id, year
        """
    ).fetchall()

    pnl = {}
    bs = {}
    cf = {}

    for row in pnl_rows:

        key = (
            row[0],
            int(row[1]),
        )

        pnl[key] = {
            "sales": safe_float(row[2]),
            "operating_profit": safe_float(row[3]),
            "opm_percentage": safe_float(row[4]),
            "other_income": safe_float(row[5]),
            "interest": safe_float(row[6]),
            "net_profit": safe_float(row[7]),
            "eps": safe_float(row[8]),
            "dividend_payout": safe_float(row[9]),
        }

    for row in bs_rows:

        key = (
            row[0],
            int(row[1]),
        )

        bs[key] = {
            "share_capital": safe_float(row[2]),
            "reserves": safe_float(row[3]),
            "borrowings": safe_float(row[4]),
            "investments": safe_float(row[5]),
            "total_assets": safe_float(row[6]),
        }

    for row in cf_rows:

        key = (
            row[0],
            int(row[1]),
        )

        cf[key] = {
            "operating_activity": safe_float(row[2]),
            "investing_activity": safe_float(row[3]),
            "financing_activity": safe_float(row[4]),
        }

    return pnl, bs, cf


def calculate_cagr_windows(
    values_by_year,
    year,
):

    result = {}

    for window in (
        3,
        5,
        10,
    ):

        value, flag = calculate_window_cagr(
            values_by_year,
            year,
            window,
        )

        result[window] = {
            "value": value,
            "flag": flag,
        }

    return result


def write_capital_allocation(rows):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        CAPITAL_ALLOCATION_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "company_id",
                "year",
                "cfo_sign",
                "cfi_sign",
                "cff_sign",
                "pattern_label",
            ]
        )

        writer.writerows(rows)


def write_edge_case_log(lines):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        EDGE_CASE_LOG,
        "w",
        encoding="utf-8",
    ) as file:

        if not lines:

            file.write(
                "No ratio anomalies were detected.\n"
            )

        else:

            for line in lines:
                file.write(
                    line + "\n"
                )


def rebuild_financial_ratios(conn):

    conn.execute(
        "DROP TABLE IF EXISTS financial_ratios"
    )

    conn.execute(
        """
        CREATE TABLE financial_ratios (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company_id TEXT NOT NULL,

            year INTEGER,

            net_profit_margin_pct REAL,

            operating_profit_margin_pct REAL,

            return_on_equity_pct REAL,

            return_on_capital_employed_pct REAL,

            return_on_assets_pct REAL,

            debt_to_equity REAL,

            high_leverage_flag INTEGER,

            interest_coverage REAL,

            icr_label TEXT,

            icr_warning_flag INTEGER,

            net_debt REAL,

            asset_turnover REAL,

            free_cash_flow_cr REAL,

            capex_cr REAL,

            earnings_per_share REAL,

            book_value_per_share REAL,

            dividend_payout_ratio_pct REAL,

            total_debt_cr REAL,

            cash_from_operations_cr REAL,

            cfo_pat_ratio REAL,

            cfo_quality TEXT,

            capex_intensity_pct REAL,

            capex_classification TEXT,

            fcf_conversion_rate_pct REAL,

            revenue_cagr_3yr REAL,

            revenue_cagr_3yr_flag TEXT,

            revenue_cagr_5yr REAL,

            revenue_cagr_5yr_flag TEXT,

            revenue_cagr_10yr REAL,

            revenue_cagr_10yr_flag TEXT,

            pat_cagr_3yr REAL,

            pat_cagr_3yr_flag TEXT,

            pat_cagr_5yr REAL,

            pat_cagr_5yr_flag TEXT,

            pat_cagr_10yr REAL,

            pat_cagr_10yr_flag TEXT,

            eps_cagr_3yr REAL,

            eps_cagr_3yr_flag TEXT,

            eps_cagr_5yr REAL,

            eps_cagr_5yr_flag TEXT,

            eps_cagr_10yr REAL,

            eps_cagr_10yr_flag TEXT,

            composite_quality_score REAL,

            FOREIGN KEY (company_id)
                REFERENCES companies(id)
        )
        """
    )


def main():

    print("=" * 70)
    print(
        "SPRINT 2 — DAY 12 RATIO ENGINE"
    )
    print("=" * 70)

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        conn.execute(
            "PRAGMA foreign_keys = ON"
        )

        source_company_data = (
            get_source_company_data(
                conn
            )
        )

        sector_map = get_sector_map(
            conn
        )

        pnl, bs, cf = get_financial_data(
            conn
        )

        print(
            f"Companies loaded: "
            f"{len(source_company_data)}"
        )

        print(
            f"P&L records: "
            f"{len(pnl)}"
        )

        print(
            f"Balance-sheet records: "
            f"{len(bs)}"
        )

        print(
            f"Cash-flow records: "
            f"{len(cf)}"
        )

        rebuild_financial_ratios(
            conn
        )

        company_years = sorted(
            pnl.keys()
        )

        revenue_history = {}
        pat_history = {}
        eps_history = {}

        for company_id, year in company_years:

            revenue_history.setdefault(
                company_id,
                {},
            )

            pat_history.setdefault(
                company_id,
                {},
            )

            eps_history.setdefault(
                company_id,
                {},
            )

            revenue_history[
                company_id
            ][year] = pnl[
                (company_id, year)
            ]["sales"]

            pat_history[
                company_id
            ][year] = pnl[
                (company_id, year)
            ]["net_profit"]

            eps_history[
                company_id
            ][year] = pnl[
                (company_id, year)
            ]["eps"]

        insert_rows = []

        capital_rows = []

        edge_cases = []

        for company_id, year in company_years:

            p = pnl[
                (company_id, year)
            ]

            b = bs.get(
                (company_id, year),
                {},
            )

            c = cf.get(
                (company_id, year),
                {},
            )

            sales = p.get("sales")

            operating_profit = p.get(
                "operating_profit"
            )

            source_opm = p.get(
                "opm_percentage"
            )

            other_income = p.get(
                "other_income"
            )

            interest = p.get(
                "interest"
            )

            net_profit = p.get(
                "net_profit"
            )

            eps = p.get(
                "eps"
            )

            dividend_payout = p.get(
                "dividend_payout"
            )

            share_capital = b.get(
                "share_capital"
            )

            reserves = b.get(
                "reserves"
            )

            borrowings = b.get(
                "borrowings"
            )

            investments = b.get(
                "investments"
            )

            total_assets = b.get(
                "total_assets"
            )

            operating_activity = c.get(
                "operating_activity"
            )

            investing_activity = c.get(
                "investing_activity"
            )

            financing_activity = c.get(
                "financing_activity"
            )

            # ------------------------------------------------
            # PROFITABILITY
            # ------------------------------------------------

            npm = net_profit_margin(
                net_profit,
                sales,
            )

            opm, opm_difference = (
                operating_profit_margin(
                    operating_profit,
                    sales,
                    source_opm,
                )
            )

            roe = return_on_equity(
                net_profit,
                share_capital,
                reserves,
            )

            roce = return_on_capital_employed(
                operating_profit,
                share_capital,
                reserves,
                borrowings,
            )

            roa = return_on_assets(
                net_profit,
                total_assets,
            )

            if (
                opm_difference is not None
                and opm_difference > 1
            ):

                edge_cases.append(
                    f"{company_id} | {year} | "
                    f"OPM mismatch | "
                    f"computed={opm:.4f} | "
                    f"source={source_opm:.4f} | "
                    f"difference={opm_difference:.4f} | "
                    f"category=formula/source discrepancy"
                )

            # ------------------------------------------------
            # LEVERAGE
            # ------------------------------------------------

            de = debt_to_equity(
                borrowings,
                share_capital,
                reserves,
            )

            sector_info = sector_map.get(
                company_id,
                {},
            )

            broad_sector = sector_info.get(
                "sector"
            )

            high_debt = high_leverage_flag(
                de,
                broad_sector,
            )

            icr = interest_coverage_ratio(
                operating_profit,
                other_income,
                interest,
            )

            icr_label = interest_coverage_label(
                icr
            )

            icr_warning = (
                interest_coverage_warning(
                    icr
                )
            )

            nd = net_debt(
                borrowings,
                investments,
            )

            turnover = asset_turnover(
                sales,
                total_assets,
            )

            # ------------------------------------------------
            # CASH FLOW
            # ------------------------------------------------

            fcf = free_cash_flow(
                operating_activity,
                investing_activity,
            )

            cfo_ratio = cfo_pat_ratio(
                operating_activity or 0,
                net_profit or 0,
            )

            cfo_quality = classify_cfo_quality(
                cfo_ratio
            )

            capex = capex_intensity(
                investing_activity or 0,
                sales or 0,
            )

            capex_class = (
                classify_capex_intensity(
                    capex
                )
            )

            fcf_conversion = (
                fcf_conversion_rate(
                    fcf,
                    operating_profit or 0,
                )
            )

            allocation_pattern = (
                capital_allocation_pattern(
                    operating_activity or 0,
                    investing_activity or 0,
                    financing_activity or 0,
                    cfo_ratio,
                )
            )

            capital_rows.append(
                [
                    company_id,
                    year,
                    sign(
                        operating_activity or 0
                    ),
                    sign(
                        investing_activity or 0
                    ),
                    sign(
                        financing_activity or 0
                    ),
                    allocation_pattern,
                ]
            )

            # ------------------------------------------------
            # CAGR
            # ------------------------------------------------

            revenue_cagr = (
                calculate_cagr_windows(
                    revenue_history[
                        company_id
                    ],
                    year,
                )
            )

            pat_cagr = (
                calculate_cagr_windows(
                    pat_history[
                        company_id
                    ],
                    year,
                )
            )

            eps_cagr = (
                calculate_cagr_windows(
                    eps_history[
                        company_id
                    ],
                    year,
                )
            )

            # ------------------------------------------------
            # SOURCE CHECKS
            # ------------------------------------------------

            source = source_company_data.get(
                company_id,
                {},
            )

            source_roce = source.get(
                "source_roce"
            )

            source_roe = source.get(
                "source_roe"
            )

            if (
                roce is not None
                and source_roce is not None
                and abs(
                    roce - source_roce
                ) > 5
            ):

                edge_cases.append(
                    f"{company_id} | {year} | "
                    f"ROCE anomaly | "
                    f"computed={roce:.4f} | "
                    f"source={source_roce:.4f} | "
                    f"difference="
                    f"{abs(roce-source_roce):.4f} | "
                    f"category="
                    f"source/formula discrepancy"
                )

            if (
                roe is not None
                and source_roe is not None
                and abs(
                    roe - source_roe
                ) > 5
            ):

                edge_cases.append(
                    f"{company_id} | {year} | "
                    f"ROE anomaly | "
                    f"computed={roe:.4f} | "
                    f"source={source_roe:.4f} | "
                    f"difference="
                    f"{abs(roe-source_roe):.4f} | "
                    f"category="
                    f"source/formula discrepancy"
                )

            # ------------------------------------------------
            # BOOK VALUE
            # ------------------------------------------------

            bvps = (
                calculate_book_value_per_share(
                    source.get("book_value"),
                    source.get("face_value"),
                )
            )

            # ------------------------------------------------
            # COMPOSITE SCORE
            # ------------------------------------------------

            composite = (
                calculate_composite_quality_score(
                    roe,
                    roce,
                    de,
                    icr,
                    revenue_cagr[5]["value"],
                    pat_cagr[5]["value"],
                )
            )

            # ------------------------------------------------
            # EXACTLY 45 INSERT VALUES
            # ------------------------------------------------

            insert_rows.append(
                (
                    company_id,                       # 1
                    year,                              # 2
                    npm,                               # 3
                    opm,                               # 4
                    roe,                               # 5
                    roce,                              # 6
                    roa,                               # 7
                    de,                                # 8
                    int(high_debt),                   # 9
                    icr,                               # 10
                    icr_label,                         # 11
                    int(icr_warning),                 # 12
                    nd,                                # 13
                    turnover,                          # 14
                    fcf,                               # 15
                    abs(investing_activity or 0),     # 16
                    eps,                               # 17
                    bvps,                              # 18
                    dividend_payout,                   # 19
                    borrowings,                         # 20
                    operating_activity,               # 21
                    cfo_ratio,                         # 22
                    cfo_quality,                       # 23
                    capex,                             # 24
                    capex_class,                       # 25
                    fcf_conversion,                    # 26
                    revenue_cagr[3]["value"],          # 27
                    revenue_cagr[3]["flag"],           # 28
                    revenue_cagr[5]["value"],          # 29
                    revenue_cagr[5]["flag"],           # 30
                    revenue_cagr[10]["value"],         # 31
                    revenue_cagr[10]["flag"],          # 32
                    pat_cagr[3]["value"],              # 33
                    pat_cagr[3]["flag"],               # 34
                    pat_cagr[5]["value"],              # 35
                    pat_cagr[5]["flag"],               # 36
                    pat_cagr[10]["value"],             # 37
                    pat_cagr[10]["flag"],              # 38
                    eps_cagr[3]["value"],              # 39
                    eps_cagr[3]["flag"],               # 40
                    eps_cagr[5]["value"],              # 41
                    eps_cagr[5]["flag"],               # 42
                    eps_cagr[10]["value"],             # 43
                    eps_cagr[10]["flag"],              # 44
                    composite,                         # 45
                )
            )

        insert_sql = """
            INSERT INTO financial_ratios (
                company_id,
                year,
                net_profit_margin_pct,
                operating_profit_margin_pct,
                return_on_equity_pct,
                return_on_capital_employed_pct,
                return_on_assets_pct,
                debt_to_equity,
                high_leverage_flag,
                interest_coverage,
                icr_label,
                icr_warning_flag,
                net_debt,
                asset_turnover,
                free_cash_flow_cr,
                capex_cr,
                earnings_per_share,
                book_value_per_share,
                dividend_payout_ratio_pct,
                total_debt_cr,
                cash_from_operations_cr,
                cfo_pat_ratio,
                cfo_quality,
                capex_intensity_pct,
                capex_classification,
                fcf_conversion_rate_pct,
                revenue_cagr_3yr,
                revenue_cagr_3yr_flag,
                revenue_cagr_5yr,
                revenue_cagr_5yr_flag,
                revenue_cagr_10yr,
                revenue_cagr_10yr_flag,
                pat_cagr_3yr,
                pat_cagr_3yr_flag,
                pat_cagr_5yr,
                pat_cagr_5yr_flag,
                pat_cagr_10yr,
                pat_cagr_10yr_flag,
                eps_cagr_3yr,
                eps_cagr_3yr_flag,
                eps_cagr_5yr,
                eps_cagr_5yr_flag,
                eps_cagr_10yr,
                eps_cagr_10yr_flag,
                composite_quality_score
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )
        """

        conn.executemany(
            insert_sql,
            insert_rows,
        )

        write_capital_allocation(
            capital_rows
        )

        write_edge_case_log(
            edge_cases
        )

        conn.commit()

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM financial_ratios
            """
        ).fetchone()[0]

        fk_errors = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        print("\nDATABASE RESULTS")
        print("-" * 70)

        print(
            f"financial_ratios rows: {count}"
        )

        print(
            f"foreign key errors: "
            f"{fk_errors}"
        )

        print(
            f"edge cases logged: "
            f"{len(edge_cases)}"
        )

        print(
            f"capital allocation rows: "
            f"{len(capital_rows)}"
        )

        print("\nKPI NON-NULL COUNTS")
        print("-" * 70)

        required_columns = [
            "net_profit_margin_pct",
            "operating_profit_margin_pct",
            "return_on_equity_pct",
            "debt_to_equity",
            "interest_coverage",
            "asset_turnover",
            "free_cash_flow_cr",
            "capex_cr",
            "earnings_per_share",
            "book_value_per_share",
            "dividend_payout_ratio_pct",
            "total_debt_cr",
            "cash_from_operations_cr",
            "revenue_cagr_5yr",
            "pat_cagr_5yr",
            "eps_cagr_5yr",
            "composite_quality_score",
        ]

        for column in required_columns:

            value = conn.execute(
                f"""
                SELECT COUNT({column})
                FROM financial_ratios
                """
            ).fetchone()[0]

            print(
                f"{column}: {value}"
            )

        print("\nOUTPUT FILES")
        print("-" * 70)

        print(
            f"capital allocation: "
            f"{CAPITAL_ALLOCATION_FILE}"
        )

        print(
            f"edge case log: "
            f"{EDGE_CASE_LOG}"
        )

        if (
            count >= 1100
            and not fk_errors
        ):

            print(
                "\nDAY 12 DATABASE LOAD: PASSED"
            )

        else:

            print(
                "\nDAY 12 DATABASE LOAD: NEEDS REVIEW"
            )

    finally:

        conn.close()


if __name__ == "__main__":
    main()
