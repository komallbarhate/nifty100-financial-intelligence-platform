"""
NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM
Day 34 - Sector Report Generator

Generates one PDF report for every sector present
in the sectors table.

Current database:
    10 sectors
    92 companies

Output:
    reports/sector/<sector>_report.pdf
"""

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

OUTPUT_DIR = ROOT / "reports" / "sector"
CHART_DIR = ROOT / "output" / "sector_charts"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

CHART_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


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


def safe_filename(value):
    """Process safe filename."""
    return re.sub(
        r"[^A-Za-z0-9_.-]+",
        "_",
        str(value),
    )


def fmt_number(value):
    """Process fmt number."""
    if value is None or pd.isna(value):
        return "N/A"

    try:
        return f"{float(value):,.1f}"
    except Exception:
        return "N/A"


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


# ============================================================
# DATA LOADING
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
        "market": read_table(
            conn,
            "market_cap",
        ),
    }


# ============================================================
# SECTOR COMPANIES
# ============================================================


def get_sector_companies(sectors, sector):
    """Return sector companies."""
    sector_col = find_column(
        sectors,
        ["sector"],
    )

    company_col = find_column(
        sectors,
        ["company_id"],
    )

    if not sector_col or not company_col:
        return []

    rows = sectors[sectors[sector_col].astype(str) == sector]

    return sorted(rows[company_col].dropna().astype(str).str.upper().unique().tolist())


# ============================================================
# COMPANY LATEST VALUES
# ============================================================


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


# ============================================================
# SECTOR METRICS
# ============================================================


def calculate_sector_metrics(
    sector,
    company_ids,
    data,
):
    """Calculate sector metrics."""
    rows = []

    companies = data["companies"]
    ratios = data["ratios"]
    pnl = data["pnl"]
    cashflow = data["cashflow"]
    market = data["market"]

    company_name_col = find_column(
        companies,
        ["company_name"],
    )

    for company_id in company_ids:
        company = company_rows(
            companies,
            company_id,
        )

        ratio = company_rows(
            ratios,
            company_id,
        )

        company_rows(
            pnl,
            company_id,
        )

        company_rows(
            cashflow,
            company_id,
        )

        market_rows = company_rows(
            market,
            company_id,
        )

        if not company.empty and company_name_col:
            name = str(company.iloc[-1][company_name_col])
        else:
            name = company_id

        roe = latest_value(
            ratio,
            ["return_on_equity_pct"],
        )

        roce = latest_value(
            ratio,
            ["return_on_capital_employed_pct"],
        )

        opm = latest_value(
            ratio,
            ["operating_profit_margin_pct"],
        )

        debt_equity = latest_value(
            ratio,
            ["debt_to_equity"],
        )

        fcf = latest_value(
            ratio,
            ["free_cash_flow_cr"],
        )

        cfo_pat = latest_value(
            ratio,
            ["cfo_pat_ratio"],
        )

        pe = latest_value(
            market_rows,
            ["pe_ratio", "pe"],
        )

        pb = latest_value(
            market_rows,
            ["pb_ratio", "pb"],
        )

        revenue_cagr = latest_value(
            ratio,
            ["revenue_cagr_5yr"],
        )

        pat_cagr = latest_value(
            ratio,
            ["pat_cagr_5yr"],
        )

        rows.append(
            {
                "company_id": company_id,
                "company_name": name,
                "ROE": roe,
                "ROCE": roce,
                "OPM": opm,
                "D/E": debt_equity,
                "FCF": fcf,
                "CFO/PAT": cfo_pat,
                "P/E": pe,
                "P/B": pb,
                "Revenue CAGR": revenue_cagr,
                "PAT CAGR": pat_cagr,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# SECTOR SUMMARY
# ============================================================


def sector_summary(metrics):
    """Process sector summary."""
    numeric_columns = [
        "ROE",
        "ROCE",
        "OPM",
        "D/E",
        "FCF",
        "CFO/PAT",
        "P/E",
        "P/B",
        "Revenue CAGR",
        "PAT CAGR",
    ]

    summary = {}

    for column in numeric_columns:
        if column in metrics:
            values = pd.to_numeric(
                metrics[column],
                errors="coerce",
            ).dropna()

            if not values.empty:
                summary[column] = {
                    "mean": values.mean(),
                    "median": values.median(),
                    "count": len(values),
                }
            else:
                summary[column] = {
                    "mean": np.nan,
                    "median": np.nan,
                    "count": 0,
                }

    return summary


# ============================================================
# TOP COMPANIES TABLE
# ============================================================


def create_company_table(metrics):
    """Create company table."""
    columns = [
        "company_id",
        "company_name",
        "ROE",
        "ROCE",
        "OPM",
        "D/E",
        "FCF",
    ]

    available = [col for col in columns if col in metrics.columns]

    display = metrics[available].copy()

    if "ROE" in display.columns:
        display["ROE"] = display["ROE"].map(fmt_pct)

    if "ROCE" in display.columns:
        display["ROCE"] = display["ROCE"].map(fmt_pct)

    if "OPM" in display.columns:
        display["OPM"] = display["OPM"].map(fmt_pct)

    if "D/E" in display.columns:
        display["D/E"] = display["D/E"].map(fmt_ratio)

    if "FCF" in display.columns:
        display["FCF"] = display["FCF"].map(
            lambda x: (fmt_number(x) if pd.notna(x) else "N/A")
        )

    headers = {
        "company_id": "Ticker",
        "company_name": "Company",
        "ROE": "ROE",
        "ROCE": "ROCE",
        "OPM": "OPM",
        "D/E": "D/E",
        "FCF": "FCF Cr",
    }

    table_rows = [
        [
            Paragraph(
                f"<b>{headers[col]}</b>",
                BODY_STYLE,
            )
            for col in available
        ]
    ]

    for _, row in display.iterrows():
        table_rows.append(
            [
                Paragraph(
                    str(row[col]),
                    SMALL_STYLE,
                )
                for col in available
            ]
        )

    widths = []

    for col in available:
        if col == "company_name":
            widths.append(48 * mm)
        elif col == "company_id":
            widths.append(23 * mm)
        else:
            widths.append(20.5 * mm)

    table = Table(
        table_rows,
        colWidths=widths,
        repeatRows=1,
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
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#D1D5DB"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        WHITE,
                        LIGHT_GREY,
                    ],
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
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
# SECTOR ROE CHART
# ============================================================


def create_sector_roe_chart(
    sector,
    metrics,
):
    """Create sector roe chart."""
    chart = metrics[
        [
            "company_id",
            "ROE",
        ]
    ].copy()

    chart["ROE"] = pd.to_numeric(
        chart["ROE"],
        errors="coerce",
    )

    chart = chart.dropna(subset=["ROE"]).sort_values(
        "ROE",
        ascending=False,
    )

    if chart.empty:
        return None

    fig, ax = plt.subplots(
        figsize=(7.2, 3.0),
        dpi=150,
    )

    x = np.arange(len(chart))

    ax.bar(
        x,
        chart["ROE"],
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        chart["company_id"],
        rotation=55,
        ha="right",
        fontsize=7,
    )

    ax.set_ylabel(
        "ROE (%)",
        fontsize=8,
    )

    ax.set_title(
        "Latest ROE by Company",
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

    plt.tight_layout()

    path = CHART_DIR / f"{safe_filename(sector)}_roe.png"

    fig.savefig(
        path,
        bbox_inches="tight",
    )

    plt.close(fig)

    return path


# ============================================================
# SECTOR REVENUE / PROFIT GROWTH CHART
# ============================================================


def create_growth_chart(
    sector,
    metrics,
):
    """Create growth chart."""
    chart = metrics[
        [
            "company_id",
            "Revenue CAGR",
            "PAT CAGR",
        ]
    ].copy()

    chart["Revenue CAGR"] = pd.to_numeric(
        chart["Revenue CAGR"],
        errors="coerce",
    )

    chart["PAT CAGR"] = pd.to_numeric(
        chart["PAT CAGR"],
        errors="coerce",
    )

    chart = chart.dropna(
        subset=[
            "Revenue CAGR",
            "PAT CAGR",
        ],
        how="all",
    )

    if chart.empty:
        return None

    x = np.arange(len(chart))

    width = 0.36

    fig, ax = plt.subplots(
        figsize=(7.2, 3.0),
        dpi=150,
    )

    revenue = chart["Revenue CAGR"].fillna(0)

    profit = chart["PAT CAGR"].fillna(0)

    ax.bar(
        x - width / 2,
        revenue,
        width,
        label="Revenue CAGR",
    )

    ax.bar(
        x + width / 2,
        profit,
        width,
        label="PAT CAGR",
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        chart["company_id"],
        rotation=55,
        ha="right",
        fontsize=7,
    )

    ax.set_ylabel(
        "5-Year CAGR (%)",
        fontsize=8,
    )

    ax.set_title(
        "5-Year Revenue and PAT CAGR",
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

    path = CHART_DIR / f"{safe_filename(sector)}_growth.png"

    fig.savefig(
        path,
        bbox_inches="tight",
    )

    plt.close(fig)

    return path


# ============================================================
# REPORT STYLES
# ============================================================

styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "SectorTitle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=21,
    textColor=WHITE,
)

SUBTITLE_STYLE = ParagraphStyle(
    "SectorSubtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=8.5,
    leading=11,
    textColor=colors.HexColor("#DCE6F2"),
)

SECTION_STYLE = ParagraphStyle(
    "SectorSection",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=12,
    textColor=NAVY,
    spaceBefore=3,
    spaceAfter=4,
)

BODY_STYLE = ParagraphStyle(
    "SectorBody",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=7.7,
    leading=10,
    textColor=DARK,
)

SMALL_STYLE = ParagraphStyle(
    "SectorSmall",
    parent=BODY_STYLE,
    fontSize=6.8,
    leading=8.2,
)

CENTER_STYLE = ParagraphStyle(
    "SectorCenter",
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
# SECTOR HEADER
# ============================================================


def create_header(
    sector,
    company_count,
):
    """Create header."""
    table = Table(
        [
            [
                Paragraph(
                    sector,
                    TITLE_STYLE,
                ),
                Paragraph(
                    f"{company_count} Companies",
                    ParagraphStyle(
                        "SectorCount",
                        parent=CENTER_STYLE,
                        textColor=WHITE,
                        fontName="Helvetica-Bold",
                    ),
                ),
            ],
            [
                Paragraph(
                    "NIFTY 100 Sector Intelligence Report",
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
# KPI SUMMARY
# ============================================================


def create_summary_table(summary):
    """Create summary table."""
    items = [
        (
            "Median ROE",
            fmt_pct(summary["ROE"]["median"]),
        ),
        (
            "Median ROCE",
            fmt_pct(summary["ROCE"]["median"]),
        ),
        (
            "Median OPM",
            fmt_pct(summary["OPM"]["median"]),
        ),
        (
            "Median D/E",
            fmt_ratio(summary["D/E"]["median"]),
        ),
        (
            "Median Revenue CAGR",
            fmt_pct(summary["Revenue CAGR"]["median"]),
        ),
        (
            "Median PAT CAGR",
            fmt_pct(summary["PAT CAGR"]["median"]),
        ),
    ]

    cells = []

    for label, value in items:
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
                8 * mm,
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
# BUILD SECTOR PDF
# ============================================================


def build_sector_report(
    sector,
    company_ids,
    data,
):
    """Build sector report."""
    metrics = calculate_sector_metrics(
        sector,
        company_ids,
        data,
    )

    summary = sector_summary(metrics)

    roe_chart = create_sector_roe_chart(
        sector,
        metrics,
    )

    growth_chart = create_growth_chart(
        sector,
        metrics,
    )

    filename = OUTPUT_DIR / f"{safe_filename(sector)}_report.pdf"

    doc = SimpleDocTemplate(
        str(filename),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
        title=f"{sector} Sector Report",
        author=("NIFTY 100 Financial Intelligence Platform"),
    )

    story = []

    # ========================================================
    # PAGE 1
    # ========================================================

    story.append(
        create_header(
            sector,
            len(company_ids),
        )
    )

    story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            "Sector Summary",
            SECTION_STYLE,
        )
    )

    story.append(create_summary_table(summary))

    story.append(Spacer(1, 5 * mm))

    if roe_chart:
        story.append(
            Image(
                str(roe_chart),
                width=174 * mm,
                height=70 * mm,
            )
        )

    story.append(Spacer(1, 3 * mm))

    if growth_chart:
        story.append(
            Image(
                str(growth_chart),
                width=174 * mm,
                height=70 * mm,
            )
        )

    story.append(PageBreak())

    # ========================================================
    # PAGE 2
    # ========================================================

    story.append(
        Paragraph(
            "Company-Level Sector Detail",
            SECTION_STYLE,
        )
    )

    story.append(create_company_table(metrics))

    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            (
                "Methodology: sector metrics are calculated "
                "from the latest available company-level "
                "financial records in the NIFTY 100 project "
                "database. Median values are used for the "
                "sector summary to reduce sensitivity to "
                "extreme observations."
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

    doc.build(
        story,
        onFirstPage=draw_page,
        onLaterPages=draw_page,
    )

    return filename


# ============================================================
# VALIDATE
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
    print("=" * 70)
    print("NIFTY 100 SECTOR REPORT GENERATOR")
    print("=" * 70)
    print()

    print(f"Database : {DB_PATH}")

    print(f"Output   : {OUTPUT_DIR}")

    print()

    conn = connect_db()

    try:
        data = load_data(conn)

        sectors = data["sectors"]

        sector_col = find_column(
            sectors,
            ["sector"],
        )

        if not sector_col:
            raise RuntimeError("Sector column not found.")

        sector_names = sorted(
            sectors[sector_col].dropna().astype(str).unique().tolist()
        )

        print(f"Sectors found : {len(sector_names)}")

        print(f"Companies     : " f"{sectors['company_id'].nunique()}")

        print()

        success = []
        failed = []

        for sector in sector_names:
            company_ids = get_sector_companies(
                sectors,
                sector,
            )

            print(
                f"Generating {sector} " f"({len(company_ids)} companies)...",
                end=" ",
            )

            try:
                path = build_sector_report(
                    sector,
                    company_ids,
                    data,
                )

                valid, message = validate_pdf(path)

                if valid:
                    success.append(sector)

                    print(f"OK ({message})")

                else:
                    failed.append(
                        (
                            sector,
                            message,
                        )
                    )

                    print(f"FAILED - {message}")

            except Exception as exc:
                failed.append(
                    (
                        sector,
                        str(exc),
                    )
                )

                print(f"FAILED - {exc}")

        print()
        print("=" * 70)
        print("SECTOR REPORT SUMMARY")
        print("=" * 70)

        print(f"Requested : {len(sector_names)}")

        print(f"Generated : {len(success)}")

        print(f"Failed    : {len(failed)}")

        if success:
            print()
            print("Successful:")

            for sector in success:
                print(f"  {sector}")

        if failed:
            print()
            print("Failures:")

            for sector, error in failed:
                print(f"  {sector}: {error}")

        print()
        print("Output directory:")

        print(f"  {OUTPUT_DIR}")

        print()

        if len(sector_names) != 11:
            print("NOTE:")

            print(
                "  The current database contains "
                f"{len(sector_names)} sectors, "
                "not 11."
            )

            print("  No artificial sector was created.")

            print()

        print("SECTOR REPORT GENERATION COMPLETE")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
