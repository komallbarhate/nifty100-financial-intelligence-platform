"""
NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM
Day 35 - Portfolio Summary

Generates one consolidated PDF containing one page per company.

Output:
    reports/portfolio/portfolio_summary.pdf

Ordering:
    Alphabetical by ticker
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
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

OUTPUT_DIR = ROOT / "reports" / "portfolio"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_FILE = OUTPUT_DIR / "portfolio_summary.pdf"


# ============================================================
# COLORS
# ============================================================

NAVY = colors.HexColor("#0B1F3A")
BLUE = colors.HexColor("#173F6D")
LIGHT_BLUE = colors.HexColor("#EAF2F8")
LIGHT_GREY = colors.HexColor("#F3F5F7")
MID_GREY = colors.HexColor("#6B7280")
DARK = colors.HexColor("#1F2937")
GREEN = colors.HexColor("#166534")
RED = colors.HexColor("#991B1B")
AMBER = colors.HexColor("#92400E")
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
# HELPERS
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

    rows = df[df[id_col].astype(str).str.upper() == company_id.upper()].copy()

    year_col = find_column(
        rows,
        ["year"],
    )

    if year_col:
        rows["_year"] = pd.to_numeric(
            rows[year_col],
            errors="coerce",
        )

        rows = rows.sort_values("_year")

    return rows


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

    try:
        return float(df.iloc[-1][column])
    except Exception:
        return np.nan


def fmt_pct(value):
    """Process fmt pct."""
    if value is None or pd.isna(value):
        return "N/A"

    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "N/A"


def fmt_ratio(value):
    """Process fmt ratio."""
    if value is None or pd.isna(value):
        return "N/A"

    try:
        return f"{float(value):.2f}x"
    except Exception:
        return "N/A"


def fmt_number(value):
    """Process fmt number."""
    if value is None or pd.isna(value):
        return "N/A"

    try:
        return f"{float(value):,.0f}"
    except Exception:
        return "N/A"


def shorten(text, maximum=110):
    """Process shorten."""
    text = str(text)

    if len(text) <= maximum:
        return text

    return text[: maximum - 3].rstrip() + "..."


# ============================================================
# LOAD DATA
# ============================================================


def load_data(conn):
    """Load data."""
    return {
        "companies": read_table(
            conn,
            "companies",
        ),
        "sectors": read_table(
            conn,
            "sectors",
        ),
        "ratios": read_table(
            conn,
            "financial_ratios",
        ),
        "pnl": read_table(
            conn,
            "profitandloss",
        ),
        "cashflow": read_table(
            conn,
            "cashflow",
        ),
        "balance": read_table(
            conn,
            "balancesheet",
        ),
        "market": read_table(
            conn,
            "market_cap",
        ),
    }


# ============================================================
# COMPANY INFO
# ============================================================


def get_company_info(company_id, data):
    """Return company info."""
    companies = data["companies"]

    rows = company_rows(
        companies,
        company_id,
    )

    company_name = company_id

    if not rows.empty:
        name_col = find_column(
            companies,
            ["company_name"],
        )

        if name_col:
            company_name = str(rows.iloc[-1][name_col])

    sector = "N/A"
    industry = "N/A"

    sectors = data["sectors"]

    sector_rows = company_rows(
        sectors,
        company_id,
    )

    if not sector_rows.empty:
        sector_col = find_column(
            sectors,
            ["sector"],
        )

        industry_col = find_column(
            sectors,
            ["industry"],
        )

        if sector_col:
            sector = str(sector_rows.iloc[-1][sector_col])

        if industry_col:
            industry = str(sector_rows.iloc[-1][industry_col])

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

    company_rows(
        data["companies"],
        company_id,
    )

    market = company_rows(
        data["market"],
        company_id,
    )

    return {
        "ROE": latest_value(
            ratios,
            ["return_on_equity_pct"],
        ),
        "ROCE": latest_value(
            ratios,
            ["return_on_capital_employed_pct"],
        ),
        "D/E": latest_value(
            ratios,
            ["debt_to_equity"],
        ),
        "FCF": latest_value(
            ratios,
            ["free_cash_flow_cr"],
        ),
        "OPM": latest_value(
            ratios,
            ["operating_profit_margin_pct"],
        ),
        "CFO/PAT": latest_value(
            ratios,
            ["cfo_pat_ratio"],
        ),
        "P/E": latest_value(
            market,
            ["pe_ratio", "pe"],
        ),
        "P/B": latest_value(
            market,
            ["pb_ratio", "pb"],
        ),
    }


# ============================================================
# TREND ARROWS
# ============================================================


def trend_arrow(
    df,
    candidates,
):
    """Process trend arrow."""
    if df.empty:
        return "→"

    column = find_column(
        df,
        candidates,
    )

    if not column:
        return "→"

    values = pd.to_numeric(
        df[column],
        errors="coerce",
    ).dropna()

    if len(values) < 2:
        return "→"

    previous = float(values.iloc[-2])

    latest = float(values.iloc[-1])

    if latest > previous * 1.03:
        return "↑"

    if latest < previous * 0.97:
        return "↓"

    return "→"


def get_trends(company_id, data):
    """Return trends."""
    ratios = company_rows(
        data["ratios"],
        company_id,
    )

    pnl = company_rows(
        data["pnl"],
        company_id,
    )

    return {
        "ROE": trend_arrow(
            ratios,
            ["return_on_equity_pct"],
        ),
        "ROCE": trend_arrow(
            ratios,
            ["return_on_capital_employed_pct"],
        ),
        "OPM": trend_arrow(
            ratios,
            ["operating_profit_margin_pct"],
        ),
        "Revenue": trend_arrow(
            pnl,
            ["sales"],
        ),
        "Net Profit": trend_arrow(
            pnl,
            ["net_profit"],
        ),
        "D/E": trend_arrow(
            ratios,
            ["debt_to_equity"],
        ),
    }


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
# PROS / CONS
# ============================================================


def get_pros_cons(company_id):
    """Return pros cons."""
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
        text = str(row[text_col])

        if confidence_col and pd.notna(row.get("_confidence")):
            text += f" " f"({float(row['_confidence']):.0f}%)"

        text = shorten(
            text,
            105,
        )

        kind = str(row[type_col]).lower()

        if kind == "pro":
            pros.append(text)

        elif kind == "con":
            cons.append(text)

    return pros[:3], cons[:3]


# ============================================================
# STYLES
# ============================================================

styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "PortfolioTitle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=19,
    leading=22,
    textColor=WHITE,
)

SUBTITLE_STYLE = ParagraphStyle(
    "PortfolioSubtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=8.5,
    leading=11,
    textColor=colors.HexColor("#DCE6F2"),
)

SECTION_STYLE = ParagraphStyle(
    "PortfolioSection",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=12,
    textColor=NAVY,
    spaceBefore=3,
    spaceAfter=4,
)

BODY_STYLE = ParagraphStyle(
    "PortfolioBody",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=7.7,
    leading=10,
    textColor=DARK,
)

SMALL_STYLE = ParagraphStyle(
    "PortfolioSmall",
    parent=BODY_STYLE,
    fontSize=7,
    leading=8.5,
)

CENTER_STYLE = ParagraphStyle(
    "PortfolioCenter",
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
# COMPANY HEADER
# ============================================================


def create_company_header(
    company_id,
    info,
):
    """Create company header."""
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
                        "TickerHeader",
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
# KPI TABLE
# ============================================================


def create_kpi_table(
    kpis,
    trends,
):
    """Create kpi table."""
    data = [
        [
            Paragraph(
                "<b>Metric</b>",
                BODY_STYLE,
            ),
            Paragraph(
                "<b>Value</b>",
                BODY_STYLE,
            ),
            Paragraph(
                "<b>Trend</b>",
                BODY_STYLE,
            ),
        ],
        [
            "ROE",
            fmt_pct(kpis["ROE"]),
            trends["ROE"],
        ],
        [
            "ROCE",
            fmt_pct(kpis["ROCE"]),
            trends["ROCE"],
        ],
        [
            "Operating Margin",
            fmt_pct(kpis["OPM"]),
            trends["OPM"],
        ],
        [
            "Debt / Equity",
            fmt_ratio(kpis["D/E"]),
            trends["D/E"],
        ],
        [
            "Free Cash Flow",
            (fmt_number(kpis["FCF"]) + " Cr" if not pd.isna(kpis["FCF"]) else "N/A"),
            "→",
        ],
        [
            "CFO / PAT",
            fmt_ratio(kpis["CFO/PAT"]),
            "→",
        ],
        [
            "P/E",
            fmt_ratio(kpis["P/E"]),
            "→",
        ],
        [
            "P/B",
            fmt_ratio(kpis["P/B"]),
            "→",
        ],
    ]

    formatted = []

    for row_index, row in enumerate(data):
        formatted_row = []

        for col_index, value in enumerate(row):
            if row_index == 0:
                formatted_row.append(value)
            else:
                if col_index == 2:
                    formatted_row.append(
                        Paragraph(
                            f"<b>{value}</b>",
                            CENTER_STYLE,
                        )
                    )
                else:
                    formatted_row.append(
                        Paragraph(
                            str(value),
                            BODY_STYLE,
                        )
                    )

        formatted.append(formatted_row)

    table = Table(
        formatted,
        colWidths=[
            60 * mm,
            70 * mm,
            35 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    LIGHT_BLUE,
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
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (2, 1),
                    (2, -1),
                    "CENTER",
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
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    return table


# ============================================================
# PROS / CONS
# ============================================================


def create_pros_cons_table(
    pros,
    cons,
):
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
        pro = (
            "• " + pros[i]
            if i < len(pros)
            else "• No significant positive signal triggered."
        )

        con = (
            "• " + cons[i]
            if i < len(cons)
            else "• No significant negative signal triggered."
        )

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
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    return table


# ============================================================
# CAPITAL ALLOCATION
# ============================================================


def create_capital_table(pattern):
    """Create capital table."""
    table = Table(
        [
            [
                Paragraph(
                    "<b>Latest Capital Allocation Pattern</b>",
                    BODY_STYLE,
                )
            ],
            [
                Paragraph(
                    shorten(pattern, 100),
                    CENTER_STYLE,
                )
            ],
        ],
        colWidths=[174 * mm],
        rowHeights=[
            8 * mm,
            12 * mm,
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
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    WHITE,
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
# BUILD ONE COMPANY PAGE
# ============================================================


def add_company_page(
    story,
    company_id,
    data,
):
    """Process add company page."""
    info = get_company_info(
        company_id,
        data,
    )

    kpis = get_kpis(
        company_id,
        data,
    )

    trends = get_trends(
        company_id,
        data,
    )

    pattern = get_capital_allocation(
        company_id,
    )

    pros, cons = get_pros_cons(
        company_id,
    )

    story.append(
        create_company_header(
            company_id,
            info,
        )
    )

    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            "Key Metrics & Trends",
            SECTION_STYLE,
        )
    )

    story.append(
        create_kpi_table(
            kpis,
            trends,
        )
    )

    story.append(Spacer(1, 5 * mm))

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

    story.append(Spacer(1, 5 * mm))

    story.append(
        create_capital_table(
            pattern,
        )
    )

    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            (
                "Trend arrows compare the latest available "
                "observation with the preceding observation. "
                "↑ indicates an increase, ↓ indicates a decrease, "
                "and → indicates broadly stable movement."
            ),
            SMALL_STYLE,
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


# ============================================================
# MAIN
# ============================================================


def main():
    """Run the main workflow."""
    print("=" * 70)
    print("NIFTY 100 PORTFOLIO SUMMARY GENERATOR")
    print("=" * 70)
    print()

    print(f"Database : {DB_PATH}")

    print(f"Output   : {OUTPUT_FILE}")

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

        company_ids = sorted(
            companies[id_col].dropna().astype(str).str.upper().unique().tolist()
        )

        print(f"Companies : {len(company_ids)}")

        print("Ordering   : Alphabetical by ticker")

        print()

        doc = SimpleDocTemplate(
            str(OUTPUT_FILE),
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=12 * mm,
            bottomMargin=14 * mm,
            title=("NIFTY 100 Portfolio Summary"),
            author=("NIFTY 100 Financial Intelligence Platform"),
        )

        story = []

        for index, company_id in enumerate(company_ids):
            print(f"Adding {company_id} " f"({index + 1}/{len(company_ids)})...")

            add_company_page(
                story,
                company_id,
                data,
            )

            if index < len(company_ids) - 1:
                story.append(PageBreak())

        doc.build(
            story,
            onFirstPage=draw_page,
            onLaterPages=draw_page,
        )

        size_kb = OUTPUT_FILE.stat().st_size / 1024

        print()
        print("=" * 70)
        print("PORTFOLIO SUMMARY COMPLETE")
        print("=" * 70)

        print(f"Companies : {len(company_ids)}")

        print(f"Pages     : {len(company_ids)}")

        print(f"PDF size  : {size_kb:.1f} KB")

        print(f"Output    : {OUTPUT_FILE}")

        print()
        print("PORTFOLIO SUMMARY GENERATION COMPLETE")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
