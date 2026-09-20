"""
NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM
Day 33 - Company Tearsheet Generator

Test:
    python src/reports/tearsheet.py

All 92:
    python src/reports/tearsheet.py --all
"""

import argparse
import re
import sqlite3
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "data" / "nifty100.db"

OUTPUT_DIR = ROOT / "reports" / "tearsheets"
CHART_DIR = ROOT / "output" / "tearsheet_charts"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# TEST COMPANIES
# ============================================================

TEST_COMPANIES = [
    "TCS",
    "HDFCBANK",
    "RELIANCE",
    "SUNPHARMA",
    "TATASTEEL",
]


# ============================================================
# COLORS
# ============================================================

NAVY = colors.HexColor("#0B1F3A")
LIGHT_BLUE = colors.HexColor("#EAF2F8")
LIGHT_GREY = colors.HexColor("#F3F5F7")
MID_GREY = colors.HexColor("#6B7280")
DARK = colors.HexColor("#1F2937")
WHITE = colors.white


# ============================================================
# DATABASE
# ============================================================


def connect_db():
    """Process connect db."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    return sqlite3.connect(DB_PATH)


def read_table(conn, table_name):
    """Process read table."""
    exists = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name=?
        """,
        (table_name,),
    ).fetchone()

    if not exists:
        return pd.DataFrame()

    return pd.read_sql_query(
        f'SELECT * FROM "{table_name}"',
        conn,
    )


# ============================================================
# GENERAL HELPERS
# ============================================================


def find_column(df, candidates):
    """Find column."""
    if df.empty:
        return None

    mapping = {str(col).lower(): col for col in df.columns}

    for candidate in candidates:
        if candidate.lower() in mapping:
            return mapping[candidate.lower()]

    return None


def company_rows(df, company_id):
    """Process company rows."""
    if df.empty:
        return pd.DataFrame()

    id_col = find_column(
        df,
        ["company_id", "id"],
    )

    if not id_col:
        return pd.DataFrame()

    result = df[df[id_col].astype(str).str.upper() == company_id.upper()].copy()

    year_col = find_column(
        result,
        ["year", "financial_year"],
    )

    if year_col:
        result["_year"] = pd.to_numeric(
            result[year_col],
            errors="coerce",
        )

        result = result.sort_values("_year")

    return result


def latest_value(df, candidates):
    """Process latest value."""
    if df.empty:
        return np.nan

    column = find_column(
        df,
        candidates,
    )

    if not column:
        return np.nan

    value = df.iloc[-1][column]

    try:
        return float(value)
    except Exception:
        return np.nan


def fmt_pct(value):
    """Process fmt pct."""
    if value is None or pd.isna(value):
        return "N/A"

    return f"{float(value):.1f}%"


def fmt_ratio(value):
    """Process fmt ratio."""
    if value is None or pd.isna(value):
        return "N/A"

    return f"{float(value):.2f}x"


def fmt_number(value):
    """Process fmt number."""
    if value is None or pd.isna(value):
        return "N/A"

    return f"{float(value):,.0f}"


def safe_filename(value):
    """Process safe filename."""
    return re.sub(
        r"[^A-Za-z0-9_.-]",
        "_",
        str(value),
    )


def shorten(text, maximum=120):
    """Process shorten."""
    text = str(text)

    if len(text) <= maximum:
        return text

    return text[: maximum - 3].rstrip() + "..."


# ============================================================
# LOAD ALL DATA
# ============================================================


def load_data(conn):
    """Load data."""
    return {
        "companies": read_table(
            conn,
            "companies",
        ),
        "ratios": read_table(
            conn,
            "financial_ratios",
        ),
        "pnl": read_table(
            conn,
            "profitandloss",
        ),
        "balance": read_table(
            conn,
            "balancesheet",
        ),
        "cashflow": read_table(
            conn,
            "cashflow",
        ),
        "sectors": read_table(
            conn,
            "sectors",
        ),
        "market": read_table(
            conn,
            "market_cap",
        ),
    }


# ============================================================
# COMPANY INFORMATION
# ============================================================


def get_company_info(company_id, data):
    """Return company info."""
    companies = data["companies"]

    rows = company_rows(
        companies,
        company_id,
    )

    if rows.empty:
        company_name = company_id
    else:
        name_col = find_column(
            companies,
            ["company_name", "name"],
        )

        if name_col:
            company_name = str(rows.iloc[-1][name_col])
        else:
            company_name = company_id

    sector = "N/A"
    industry = "N/A"

    sectors = data["sectors"]

    srows = company_rows(
        sectors,
        company_id,
    )

    if not srows.empty:
        sector_col = find_column(
            sectors,
            ["sector"],
        )

        industry_col = find_column(
            sectors,
            ["industry"],
        )

        if sector_col:
            sector = str(srows.iloc[-1][sector_col])

        if industry_col:
            industry = str(srows.iloc[-1][industry_col])

    return {
        "company_name": company_name,
        "sector": sector,
        "industry": industry,
    }


# ============================================================
# KPI DATA
# ============================================================


def get_kpis(company_id, data):
    """Return kpis."""
    ratios = company_rows(
        data["ratios"],
        company_id,
    )

    companies = company_rows(
        data["companies"],
        company_id,
    )

    market = company_rows(
        data["market"],
        company_id,
    )

    kpis = {}

    kpis["ROE"] = latest_value(
        ratios,
        ["return_on_equity_pct"],
    )

    kpis["ROCE"] = latest_value(
        ratios,
        ["return_on_capital_employed_pct"],
    )

    if pd.isna(kpis["ROCE"]):
        kpis["ROCE"] = latest_value(
            companies,
            ["roce_percentage"],
        )

    kpis["D/E"] = latest_value(
        ratios,
        ["debt_to_equity"],
    )

    kpis["FCF"] = latest_value(
        ratios,
        ["free_cash_flow_cr"],
    )

    kpis["OPM"] = latest_value(
        ratios,
        ["operating_profit_margin_pct"],
    )

    kpis["CFO/PAT"] = latest_value(
        ratios,
        ["cfo_pat_ratio"],
    )

    kpis["P/E"] = latest_value(
        market,
        ["pe_ratio", "pe"],
    )

    kpis["P/B"] = latest_value(
        market,
        ["pb_ratio", "pb"],
    )

    return kpis


# ============================================================
# REVENUE + PROFIT CHART
# ============================================================


def create_revenue_profit_chart(company_id, data):
    """Create revenue profit chart."""
    pnl = company_rows(
        data["pnl"],
        company_id,
    )

    if pnl.empty:
        return None

    year_col = find_column(
        pnl,
        ["year"],
    )

    sales_col = find_column(
        pnl,
        ["sales"],
    )

    profit_col = find_column(
        pnl,
        ["net_profit"],
    )

    if not all([year_col, sales_col, profit_col]):
        return None

    chart = pnl[[year_col, sales_col, profit_col]].copy()

    chart["year"] = pd.to_numeric(
        chart[year_col],
        errors="coerce",
    )

    chart["sales"] = pd.to_numeric(
        chart[sales_col],
        errors="coerce",
    )

    chart["profit"] = pd.to_numeric(
        chart[profit_col],
        errors="coerce",
    )

    chart = chart.dropna(
        subset=[
            "year",
            "sales",
            "profit",
        ]
    ).tail(10)

    if chart.empty:
        return None

    x = np.arange(len(chart))
    width = 0.36

    fig, ax = plt.subplots(
        figsize=(7.2, 2.55),
        dpi=150,
    )

    ax.bar(
        x - width / 2,
        chart["sales"],
        width,
        label="Revenue",
    )

    ax.bar(
        x + width / 2,
        chart["profit"],
        width,
        label="Net Profit",
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        chart["year"].astype(int).astype(str),
        fontsize=7,
    )

    ax.set_title(
        "10-Year Revenue and Net Profit",
        fontsize=10,
        loc="left",
        fontweight="bold",
    )

    ax.tick_params(
        axis="y",
        labelsize=7,
    )

    ax.legend(
        fontsize=7,
        frameon=False,
        ncol=2,
        loc="upper left",
    )

    ax.grid(
        axis="y",
        alpha=0.2,
        linewidth=0.6,
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    path = CHART_DIR / f"{safe_filename(company_id)}_revenue_profit.png"

    fig.savefig(
        path,
        bbox_inches="tight",
    )

    plt.close(fig)

    return path


# ============================================================
# ROE + ROCE CHART
# ============================================================


def create_roe_roce_chart(company_id, data):
    """Create roe roce chart."""
    ratios = company_rows(
        data["ratios"],
        company_id,
    )

    if ratios.empty:
        return None

    year_col = find_column(
        ratios,
        ["year"],
    )

    roe_col = find_column(
        ratios,
        ["return_on_equity_pct"],
    )

    roce_col = find_column(
        ratios,
        ["return_on_capital_employed_pct"],
    )

    if not all([year_col, roe_col, roce_col]):
        return None

    chart = ratios[[year_col, roe_col, roce_col]].copy()

    chart["year"] = pd.to_numeric(
        chart[year_col],
        errors="coerce",
    )

    chart["roe"] = pd.to_numeric(
        chart[roe_col],
        errors="coerce",
    )

    chart["roce"] = pd.to_numeric(
        chart[roce_col],
        errors="coerce",
    )

    chart = chart.dropna(subset=["year"]).tail(10)

    if chart.empty:
        return None

    fig, ax = plt.subplots(
        figsize=(7.2, 2.45),
        dpi=150,
    )

    ax.plot(
        chart["year"],
        chart["roe"],
        marker="o",
        linewidth=1.8,
        markersize=3,
        label="ROE",
    )

    ax.plot(
        chart["year"],
        chart["roce"],
        marker="o",
        linewidth=1.8,
        markersize=3,
        label="ROCE",
    )

    ax.set_title(
        "ROE and ROCE Trend",
        fontsize=10,
        loc="left",
        fontweight="bold",
    )

    ax.set_ylabel(
        "%",
        fontsize=8,
    )

    ax.tick_params(
        axis="both",
        labelsize=7,
    )

    ax.legend(
        fontsize=7,
        frameon=False,
        ncol=2,
        loc="upper left",
    )

    ax.grid(
        alpha=0.2,
        linewidth=0.6,
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    path = CHART_DIR / f"{safe_filename(company_id)}_roe_roce.png"

    fig.savefig(
        path,
        bbox_inches="tight",
    )

    plt.close(fig)

    return path


# ============================================================
# BALANCE SHEET CHART
#
# EXACT DATABASE SCHEMA:
# id
# company_id
# year
# share_capital
# reserves
# borrowings
# other_liabilities
# total_liabilities
# fixed_assets
# cwip
# investments
# other_assets
# total_assets
# ============================================================


def create_balance_chart(company_id, data):
    """Create balance chart."""
    balance = company_rows(
        data["balance"],
        company_id,
    )

    if balance.empty:
        return None

    year_col = find_column(
        balance,
        ["year"],
    )

    borrowings_col = find_column(
        balance,
        ["borrowings"],
    )

    share_capital_col = find_column(
        balance,
        ["share_capital"],
    )

    reserves_col = find_column(
        balance,
        ["reserves"],
    )

    if not year_col:
        return None

    chart = balance.copy()

    chart["year"] = pd.to_numeric(
        chart[year_col],
        errors="coerce",
    )

    # Exact database mapping
    chart["borrowings"] = (
        pd.to_numeric(
            chart[borrowings_col],
            errors="coerce",
        )
        if borrowings_col
        else 0.0
    )

    chart["share_capital"] = (
        pd.to_numeric(
            chart[share_capital_col],
            errors="coerce",
        )
        if share_capital_col
        else 0.0
    )

    chart["reserves"] = (
        pd.to_numeric(
            chart[reserves_col],
            errors="coerce",
        )
        if reserves_col
        else 0.0
    )

    # Equity = share capital + reserves
    chart["equity"] = chart["share_capital"].fillna(0) + chart["reserves"].fillna(0)

    chart = chart.dropna(subset=["year"]).tail(8)

    if chart.empty:
        return None

    chart["borrowings"] = chart["borrowings"].fillna(0)

    chart["equity"] = chart["equity"].fillna(0)

    fig, ax = plt.subplots(
        figsize=(7.2, 2.35),
        dpi=150,
    )

    x = np.arange(len(chart))

    # Actual stacked bars
    ax.bar(
        x,
        chart["borrowings"],
        label="Borrowings",
    )

    ax.bar(
        x,
        chart["equity"],
        bottom=chart["borrowings"],
        label="Equity",
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        chart["year"].astype(int).astype(str),
        fontsize=7,
    )

    ax.tick_params(
        axis="y",
        labelsize=7,
    )

    ax.set_title(
        "Balance Sheet Structure",
        fontsize=10,
        loc="left",
        fontweight="bold",
    )

    ax.legend(
        fontsize=7,
        frameon=False,
        ncol=2,
        loc="upper left",
    )

    ax.grid(
        axis="y",
        alpha=0.2,
        linewidth=0.6,
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    path = CHART_DIR / f"{safe_filename(company_id)}_balance.png"

    fig.savefig(
        path,
        bbox_inches="tight",
    )

    plt.close(fig)

    return path


# ============================================================
# CASH FLOW CHART
# ============================================================


def create_cashflow_chart(company_id, data):
    """Create cashflow chart."""
    cashflow = company_rows(
        data["cashflow"],
        company_id,
    )

    if cashflow.empty:
        return None

    cfo_col = find_column(
        cashflow,
        ["operating_activity"],
    )

    cfi_col = find_column(
        cashflow,
        ["investing_activity"],
    )

    cff_col = find_column(
        cashflow,
        ["financing_activity"],
    )

    if not any([cfo_col, cfi_col, cff_col]):
        return None

    latest = cashflow.iloc[-1]

    items = []

    for label, column in [
        ("CFO", cfo_col),
        ("CFI", cfi_col),
        ("CFF", cff_col),
    ]:
        if column:
            try:
                value = float(latest[column])

                if pd.notna(value):
                    items.append((label, value))
            except Exception:
                pass

    if not items:
        return None

    labels = [item[0] for item in items]

    values = [item[1] for item in items]

    net = sum(values)

    labels.append("Net")
    values.append(net)

    fig, ax = plt.subplots(
        figsize=(7.2, 2.35),
        dpi=150,
    )

    x = np.arange(len(values))

    bars = ax.bar(
        x,
        values,
    )

    ax.axhline(
        0,
        linewidth=0.8,
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        labels,
        fontsize=8,
    )

    ax.set_title(
        "Latest-Year Cash Flow",
        fontsize=10,
        loc="left",
        fontweight="bold",
    )

    ax.tick_params(
        axis="y",
        labelsize=7,
    )

    ax.grid(
        axis="y",
        alpha=0.2,
        linewidth=0.6,
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar, value in zip(
        bars,
        values,
    ):
        offset = max(
            abs(value) * 0.04,
            1,
        )

        if value >= 0:
            y = value + offset
            va = "bottom"
        else:
            y = value - offset
            va = "top"

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            fmt_number(value),
            ha="center",
            va=va,
            fontsize=7,
        )

    plt.tight_layout()

    path = CHART_DIR / f"{safe_filename(company_id)}_cashflow.png"

    fig.savefig(
        path,
        bbox_inches="tight",
    )

    plt.close(fig)

    return path


# ============================================================
# PROS / CONS
# ============================================================


def load_pros_cons(company_id):
    """Load pros cons."""
    path = ROOT / "output" / "pros_cons_generated.csv"

    if not path.exists():
        return [], []

    df = pd.read_csv(path)

    id_col = find_column(
        df,
        ["company_id"],
    )

    type_col = find_column(
        df,
        ["type"],
    )

    text_col = find_column(
        df,
        ["text"],
    )

    confidence_col = find_column(
        df,
        ["confidence_pct"],
    )

    if not all(
        [
            id_col,
            type_col,
            text_col,
        ]
    ):
        return [], []

    rows = df[df[id_col].astype(str).str.upper() == company_id.upper()].copy()

    if confidence_col:
        rows["_confidence"] = pd.to_numeric(
            rows[confidence_col],
            errors="coerce",
        )

        rows = rows.sort_values(
            "_confidence",
            ascending=False,
        )

    pros = []
    cons = []

    for _, row in rows.iterrows():
        confidence = ""

        if confidence_col and pd.notna(row.get("_confidence")):
            confidence = f" " f"({float(row['_confidence']):.0f}% confidence)"

        item = shorten(
            str(row[text_col]) + confidence,
            125,
        )

        if str(row[type_col]).lower() == "pro":
            pros.append(item)

        elif str(row[type_col]).lower() == "con":
            cons.append(item)

    return pros[:5], cons[:5]


def create_pros_cons_table(pros, cons):
    """Create pros cons table."""
    rows = [
        [
            Paragraph(
                "<b>Pros</b>",
                BODY_STYLE,
            ),
            Paragraph(
                "<b>Cons</b>",
                BODY_STYLE,
            ),
        ]
    ]

    count = max(
        len(pros),
        len(cons),
        1,
    )

    for i in range(count):
        if i < len(pros):
            pro = "• " + pros[i]
        else:
            pro = "• No significant positive " "signal triggered."

        if i < len(cons):
            con = "• " + cons[i]
        else:
            con = "• No significant negative " "signal triggered."

        rows.append(
            [
                Paragraph(
                    pro,
                    SMALL_STYLE,
                ),
                Paragraph(
                    con,
                    SMALL_STYLE,
                ),
            ]
        )

    table = Table(
        rows,
        colWidths=[
            87 * mm,
            87 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, 0),
                    colors.HexColor("#E8F5E9"),
                ),
                (
                    "BACKGROUND",
                    (1, 0),
                    (1, 0),
                    colors.HexColor("#FDECEC"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#D1D5DB"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    return table


# ============================================================
# CAPITAL ALLOCATION
# ============================================================


def get_capital_allocation(company_id):
    """Return capital allocation."""
    path = ROOT / "output" / "capital_allocation_history.csv"

    if not path.exists():
        return "N/A"

    df = pd.read_csv(path)

    id_col = find_column(
        df,
        ["company_id"],
    )

    pattern_col = find_column(
        df,
        ["capital_allocation_pattern"],
    )

    year_col = find_column(
        df,
        ["year"],
    )

    if not id_col or not pattern_col:
        return "N/A"

    rows = df[df[id_col].astype(str).str.upper() == company_id.upper()].copy()

    if rows.empty:
        return "N/A"

    if year_col:
        rows["_year"] = pd.to_numeric(
            rows[year_col],
            errors="coerce",
        )

        rows = rows.sort_values("_year")

    return str(rows.iloc[-1][pattern_col])


# ============================================================
# REPORT STYLES
# ============================================================

styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "TearsheetTitle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=19,
    leading=22,
    textColor=WHITE,
)

SUBTITLE_STYLE = ParagraphStyle(
    "TearsheetSubtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=8.5,
    leading=11,
    textColor=colors.HexColor("#DCE6F2"),
)

SECTION_STYLE = ParagraphStyle(
    "Section",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=12,
    textColor=NAVY,
    spaceBefore=3,
    spaceAfter=4,
)

BODY_STYLE = ParagraphStyle(
    "BodyCustom",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=7.7,
    leading=10,
    textColor=DARK,
)

SMALL_STYLE = ParagraphStyle(
    "SmallCustom",
    parent=BODY_STYLE,
    fontSize=7,
    leading=8.5,
)

CENTER_STYLE = ParagraphStyle(
    "CenterCustom",
    parent=BODY_STYLE,
    alignment=TA_CENTER,
)


# ============================================================
# PAGE FOOTER
# ============================================================


def draw_page(canvas, doc):
    """Process draw page."""
    canvas.saveState()

    canvas.setStrokeColor(colors.HexColor("#D9DEE5"))

    canvas.setLineWidth(0.4)

    canvas.line(
        15 * mm,
        10 * mm,
        A4[0] - 15 * mm,
        10 * mm,
    )

    canvas.setFont(
        "Helvetica",
        6.5,
    )

    canvas.setFillColor(MID_GREY)

    canvas.drawString(
        15 * mm,
        6 * mm,
        "NIFTY 100 Financial Intelligence Platform",
    )

    canvas.drawRightString(
        A4[0] - 15 * mm,
        6 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# HEADER
# ============================================================


def create_header(company_id, info):
    """Create header."""
    table = Table(
        [
            [
                Paragraph(
                    info["company_name"],
                    TITLE_STYLE,
                ),
                Paragraph(
                    company_id,
                    ParagraphStyle(
                        "Ticker",
                        parent=CENTER_STYLE,
                        textColor=WHITE,
                        fontName="Helvetica-Bold",
                    ),
                ),
            ],
            [
                Paragraph(
                    (f"Sector: {info['sector']} " f"| Industry: {info['industry']}"),
                    SUBTITLE_STYLE,
                ),
                "",
            ],
        ],
        colWidths=[
            145 * mm,
            30 * mm,
        ],
        rowHeights=[
            13 * mm,
            8 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    NAVY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "SPAN",
                    (0, 1),
                    (1, 1),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    return table


# ============================================================
# KPI TILES
# ============================================================


def create_kpi_tiles(kpis):
    """Create kpi tiles."""
    values = [
        ("ROE", fmt_pct(kpis["ROE"])),
        ("ROCE", fmt_pct(kpis["ROCE"])),
        ("D/E", fmt_ratio(kpis["D/E"])),
        (
            "FCF",
            (fmt_number(kpis["FCF"]) + " Cr" if not pd.isna(kpis["FCF"]) else "N/A"),
        ),
        ("OPM", fmt_pct(kpis["OPM"])),
        (
            "CFO/PAT",
            fmt_ratio(kpis["CFO/PAT"]),
        ),
    ]

    cells = []

    for label, value in values:
        tile = Table(
            [
                [
                    Paragraph(
                        label,
                        CENTER_STYLE,
                    )
                ],
                [
                    Paragraph(
                        f"<b>{value}</b>",
                        CENTER_STYLE,
                    )
                ],
            ],
            colWidths=[28 * mm],
            rowHeights=[
                7 * mm,
                10 * mm,
            ],
        )

        tile.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        LIGHT_BLUE,
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#CBD5E1"),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                ]
            )
        )

        cells.append(tile)

    outer = Table(
        [cells],
        colWidths=[29.2 * mm] * 6,
    )

    outer.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    1,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    1,
                ),
            ]
        )
    )

    return outer


# ============================================================
# CAPITAL ALLOCATION BADGE
# ============================================================


def create_capital_badge(pattern):
    """Create capital badge."""
    table = Table(
        [
            [
                Paragraph(
                    "<b>CAPITAL ALLOCATION</b>",
                    ParagraphStyle(
                        "White",
                        parent=CENTER_STYLE,
                        textColor=WHITE,
                        fontName="Helvetica-Bold",
                    ),
                )
            ],
            [
                Paragraph(
                    shorten(pattern, 70),
                    CENTER_STYLE,
                )
            ],
        ],
        colWidths=[174 * mm],
        rowHeights=[
            7 * mm,
            10 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    NAVY,
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, 1),
                    LIGHT_BLUE,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    return table


# ============================================================
# BUILD PDF
# ============================================================


def build_tearsheet(company_id, data):
    """Build tearsheet."""
    info = get_company_info(
        company_id,
        data,
    )

    kpis = get_kpis(
        company_id,
        data,
    )

    pros, cons = load_pros_cons(
        company_id,
    )

    capital_pattern = get_capital_allocation(
        company_id,
    )

    revenue_chart = create_revenue_profit_chart(
        company_id,
        data,
    )

    roe_chart = create_roe_roce_chart(
        company_id,
        data,
    )

    balance_chart = create_balance_chart(
        company_id,
        data,
    )

    cashflow_chart = create_cashflow_chart(
        company_id,
        data,
    )

    output_file = OUTPUT_DIR / f"{safe_filename(company_id)}_tearsheet.pdf"

    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
        title=f"{company_id} Company Tearsheet",
        author=("NIFTY 100 Financial Intelligence Platform"),
    )

    story = []

    # ========================================================
    # PAGE 1
    # ========================================================

    story.append(
        create_header(
            company_id,
            info,
        )
    )

    story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            "Key Financial Indicators",
            SECTION_STYLE,
        )
    )

    story.append(create_kpi_tiles(kpis))

    story.append(Spacer(1, 4 * mm))

    if revenue_chart:
        story.append(
            Image(
                str(revenue_chart),
                width=174 * mm,
                height=64 * mm,
            )
        )

    if roe_chart:
        story.append(
            Image(
                str(roe_chart),
                width=174 * mm,
                height=61 * mm,
            )
        )

    story.append(PageBreak())

    # ========================================================
    # PAGE 2
    # ========================================================

    story.append(
        Paragraph(
            "Balance Sheet & Cash Flow Intelligence",
            SECTION_STYLE,
        )
    )

    if balance_chart:
        story.append(
            Image(
                str(balance_chart),
                width=174 * mm,
                height=57 * mm,
            )
        )

    story.append(Spacer(1, 2 * mm))

    if cashflow_chart:
        story.append(
            Image(
                str(cashflow_chart),
                width=174 * mm,
                height=57 * mm,
            )
        )

    story.append(Spacer(1, 2 * mm))

    story.append(
        Paragraph(
            "Automated Fundamental Signals",
            SECTION_STYLE,
        )
    )

    story.append(
        create_pros_cons_table(
            pros,
            cons,
        )
    )

    story.append(Spacer(1, 4 * mm))

    story.append(
        create_capital_badge(
            capital_pattern,
        )
    )

    story.append(Spacer(1, 3 * mm))

    story.append(
        Paragraph(
            (
                "Source: NIFTY 100 project SQLite database "
                "and generated analytical outputs. Figures "
                "are presented for analytical use and should "
                "be interpreted together with the underlying "
                "financial statements."
            ),
            SMALL_STYLE,
        )
    )

    doc.build(
        story,
        onFirstPage=draw_page,
        onLaterPages=draw_page,
    )

    return output_file


# ============================================================
# VALIDATION
# ============================================================


def validate_pdf(path):
    """Validate pdf."""
    if not path.exists():
        return False, "PDF not created"

    size_kb = path.stat().st_size / 1024

    if size_kb < 10:
        return False, (f"PDF unusually small: {size_kb:.1f} KB")

    return True, f"{size_kb:.1f} KB"


# ============================================================
# MAIN
# ============================================================


def main():
    """Run the main workflow."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate tearsheets for all companies",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("NIFTY 100 COMPANY TEARSHEET GENERATOR")
    print("=" * 70)
    print()

    print(f"Database : {DB_PATH}")

    print(f"Output   : {OUTPUT_DIR}")

    print()

    conn = connect_db()

    try:
        data = load_data(conn)

        companies = data["companies"]

        id_col = find_column(
            companies,
            ["id", "company_id"],
        )

        if not id_col:
            raise RuntimeError("Company ID column not found.")

        all_companies = sorted(
            companies[id_col].dropna().astype(str).str.upper().unique().tolist()
        )

        if args.all:
            targets = all_companies

            print("Mode       : ALL COMPANIES")

        else:
            targets = [
                company for company in TEST_COMPANIES if company in all_companies
            ]

            print("Mode       : DAY 33 TEST")

        print(f"Companies  : {len(targets)}")

        print()

        success = []
        failed = []

        for company_id in targets:
            print(
                f"Generating {company_id}...",
                end=" ",
            )

            try:
                output_file = build_tearsheet(
                    company_id,
                    data,
                )

                valid, message = validate_pdf(output_file)

                if valid:
                    success.append(company_id)

                    print(f"OK ({message})")

                else:
                    failed.append(
                        (
                            company_id,
                            message,
                        )
                    )

                    print(f"FAILED - {message}")

            except Exception as exc:
                failed.append(
                    (
                        company_id,
                        str(exc),
                    )
                )

                print(f"FAILED - {exc}")

        print()

        print("=" * 70)
        print("TEARSHEET SUMMARY")
        print("=" * 70)

        print(f"Requested : {len(targets)}")

        print(f"Generated : {len(success)}")

        print(f"Failed    : {len(failed)}")

        if success:
            print()
            print("Successful:")

            for company in success:
                print(f"  {company}")

        if failed:
            print()
            print("Failures:")

            for company, error in failed:
                print(f"  {company}: {error}")

        print()
        print("Output directory:")

        print(f"  {OUTPUT_DIR}")

        print()
        print("TEARSHEET GENERATION COMPLETE")

    finally:
        conn.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
