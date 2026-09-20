"""Create the final Day 45 acceptance checklist PDF."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT = Path(
    "output/final_deliverables/D-23_acceptance_checklist/"
    "acceptance_checklist.pdf"
)


def build_pdf():
    """Create the Day 45 acceptance checklist PDF."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=17,
        leading=21,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "SubtitleCustom",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=9,
        leading=12,
        spaceAfter=12,
    )

    body_style = ParagraphStyle(
        "BodyCustom",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
    )

    heading_style = ParagraphStyle(
        "HeadingCustom",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        spaceBefore=8,
        spaceAfter=5,
    )

    rows = [
        ["Gate", "Acceptance criterion", "Evidence", "Status"],
        ["AC-01", "SQLite database exists and is loadable", "data/nifty100.db", "PASS"],
        ["AC-02", "92 companies present", "companies table: 92", "PASS"],
        ["AC-03", "Required ETL artifacts exist", "load_audit.csv and validation_failures.csv", "PASS"],
        ["AC-04", "Financial ratios meet planned >= 1,100 record target", "financial_ratios: 1,073 rows", "NOT MET"],
        ["AC-05", "Exploratory SQL delivered", "exploratory_queries.sql", "PASS"],
        ["AC-06", "Capital allocation delivered", "capital_allocation.csv", "PASS"],
        ["AC-07", "Screener output delivered", "screener_output.xlsx", "PASS"],
        ["AC-08", "Screener configuration delivered", "screener_config.yaml", "PASS"],
        ["AC-09", "Peer comparison delivered", "peer_comparison.xlsx", "PASS"],
        ["AC-10", "Radar charts for all companies", "92 PNG charts", "PASS"],
        ["AC-11", "Streamlit dashboard delivered", "src/dashboard/app.py", "PASS"],
        ["AC-12", "Valuation summary delivered", "valuation_summary.xlsx", "PASS"],
        ["AC-13", "Cashflow intelligence delivered", "cashflow_intelligence.xlsx", "PASS"],
        ["AC-14", "Pros/cons output delivered", "pros_cons_generated.csv", "PASS"],
        ["AC-15", "Parsed analysis delivered", "analysis_parsed.csv", "PASS"],
        ["AC-16", "Company tearsheets delivered", "92 PDF tearsheets", "PASS"],
        ["AC-17", "Sector reports delivered", "10 reports for 10 actual DB sectors", "PARTIAL"],
        ["AC-18", "Portfolio summary delivered", "portfolio_summary.pdf", "PASS"],
        ["AC-19", "KMeans labels delivered for all companies", "cluster_labels.csv: 92 rows", "PASS"],
        ["AC-20", "FastAPI/OpenAPI/Postman artifacts delivered", "FastAPI source + OpenAPI + Postman", "PASS"],
        ["AC-21", "Automated tests pass", "188 passed, 0 failed", "PASS"],
        ["AC-22", "Analyst guide >= 10 pages", "analyst_guide.pdf: 14 pages", "PASS"],
        ["AC-23", "Acceptance checklist delivered", "acceptance_checklist.pdf", "PASS"],
    ]

    table_data = []

    for row_index, row in enumerate(rows):
        formatted = []

        for value in row:
            formatted.append(
                Paragraph(
                    str(value),
                    body_style,
                )
            )

        table_data.append(formatted)

    table = Table(
        table_data,
        colWidths=[
            16 * mm,
            62 * mm,
            76 * mm,
            22 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story = [
        Paragraph(
            "NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM",
            title_style,
        ),
        Paragraph(
            "Day 45 — Final Acceptance Checklist",
            subtitle_style,
        ),
        Paragraph(
            "This checklist records the final verification results using the "
            "actual project artifacts and database state. It does not "
            "manufacture PASS results where a planned numerical target was "
            "not met.",
            body_style,
        ),
        Spacer(1, 6),
        table,
        Spacer(1, 10),
        Paragraph("Final QA Notes", heading_style),
        Paragraph(
            "<b>AC-04:</b> The financial_ratios table contains 1,073 records. "
            "The planned acceptance threshold is 1,100, so this gate is "
            "recorded as NOT MET.",
            body_style,
        ),
        Spacer(1, 4),
        Paragraph(
            "<b>AC-17:</b> The database contains 10 actual sector categories "
            "and 10 corresponding sector reports. The source plan references "
            "11 sector reports, so this gate is recorded as PARTIAL rather "
            "than inventing an additional sector.",
            body_style,
        ),
        Spacer(1, 4),
        Paragraph(
            "<b>Testing:</b> The final automated test suite completed with "
            "188 passed tests, 0 failures, 0 errors, and 0 skipped tests. "
            "Two dependency deprecation warnings were reported.",
            body_style,
        ),
        Spacer(1, 4),
        Paragraph(
            "<b>Code quality:</b> Ruff checks completed successfully with "
            "no lint errors. The Git working tree was clean after the Day "
            "44 commit.",
            body_style,
        ),
        Spacer(1, 10),
        Paragraph(
            "Final acceptance status: PARTIAL — all implemented deliverables "
            "are present and tested, with AC-04 and AC-17 documented as "
            "exceptions to the original numerical/planned targets.",
            body_style,
        ),
    ]

    document.build(story)
    print(f"Created: {OUTPUT}")
    print(f"Size: {OUTPUT.stat().st_size} bytes")


if __name__ == "__main__":
    build_pdf()
