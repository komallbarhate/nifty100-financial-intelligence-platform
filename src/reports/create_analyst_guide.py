from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "analyst_guide.pdf"


def build_analyst_guide():
    """Build the analyst guide PDF for the NIFTY 100 platform."""

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45,
        title="NIFTY 100 Financial Intelligence Platform - Analyst Guide",
        author="NIFTY 100 Financial Intelligence Platform",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "GuideTitle",
        parent=styles["Title"],
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        spaceAfter=18,
    )

    subtitle_style = ParagraphStyle(
        "GuideSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=24,
    )

    heading_style = ParagraphStyle(
        "GuideHeading",
        parent=styles["Heading1"],
        fontSize=18,
        leading=23,
        spaceBefore=8,
        spaceAfter=14,
    )

    subheading_style = ParagraphStyle(
        "GuideSubHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        spaceBefore=10,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "GuideBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
        spaceAfter=8,
    )

    bullet_style = ParagraphStyle(
        "GuideBullet",
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-8,
        spaceAfter=5,
    )

    code_style = ParagraphStyle(
        "GuideCode",
        parent=body_style,
        fontName="Courier",
        fontSize=8.5,
        leading=12,
        leftIndent=10,
        spaceBefore=5,
        spaceAfter=8,
    )

    story = []

    def add_title(text):
        """Process add title."""
        story.append(Paragraph(text, heading_style))

    def add_subtitle(text):
        """Process add subtitle."""
        story.append(Paragraph(text, subheading_style))

    def add_body(text):
        """Process add body."""
        story.append(Paragraph(text, body_style))

    def add_bullet(text):
        """Process add bullet."""
        story.append(Paragraph(f"• {text}", bullet_style))

    def add_code(text):
        """Process add code."""
        story.append(Paragraph(text.replace("\n", "<br/>"), code_style))

    def add_table(data, widths=None):
        """Process add table."""
        table = Table(data, colWidths=widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("LEADING", (0, 0), (-1, -1), 11),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 12))

    # PAGE 1
    story.append(Spacer(1, 1.3 * inch))
    story.append(Paragraph("NIFTY 100", title_style))
    story.append(Paragraph("FINANCIAL INTELLIGENCE PLATFORM", title_style))
    story.append(
        Paragraph(
            "Analyst Guide<br/>Dashboard • Analytics • Reports • REST API • Testing",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 0.5 * inch))
    add_body(
        "This guide explains how an analyst can use the NIFTY 100 Financial "
        "Intelligence Platform to explore company financials, screen companies, "
        "compare peers, review sectors, inspect trends, evaluate capital allocation "
        "and access generated reports."
    )
    add_body(
        "The platform combines a SQLite analytical database, Python financial "
        "analytics, a Streamlit dashboard, a FastAPI service and automated tests."
    )
    story.append(PageBreak())

    # PAGE 2
    add_title("1. Platform Overview")
    add_body(
        "The platform is organized into several layers. Raw financial datasets are "
        "processed through the ETL layer and stored in data/nifty100.db. Analytical "
        "modules calculate financial ratios, cash-flow metrics, valuation outputs, "
        "portfolio statistics and clustering results."
    )

    add_table(
        [
            ["Layer", "Purpose"],
            ["Data / ETL", "Loads, normalizes and validates financial datasets."],
            ["Database", "Stores company, financial, market, peer and document data."],
            [
                "Analytics",
                "Calculates KPIs, ratios, CAGR, valuation and cash-flow metrics.",
            ],
            ["Clustering", "Groups companies into five financial archetypes."],
            ["API", "Exposes analytical data through FastAPI endpoints."],
            ["Dashboard", "Provides interactive Streamlit screens for analysts."],
            [
                "Reports",
                "Provides company tearsheets, sector reports and portfolio reports.",
            ],
            ["Testing", "Validates ETL, analytics, APIs, dashboard and performance."],
        ],
        [1.2 * inch, 5.7 * inch],
    )

    add_subtitle("Main database")
    add_code("data/nifty100.db")

    add_subtitle("Main application commands")
    add_code(
        "python -m streamlit run src/dashboard/app.py\n"
        "uvicorn src.api.main:app --reload --port 8000\n"
        "pytest -q"
    )

    story.append(PageBreak())

    # PAGE 3
    add_title("2. Dashboard Navigation")
    add_body(
        "The Streamlit application contains eight screens. They are implemented "
        "under src/dashboard/pages and are accessed from the Streamlit navigation."
    )

    add_table(
        [
            ["Screen", "File", "Primary purpose"],
            ["Home", "01_home.py", "Platform overview and key information."],
            ["Profile", "02_profile.py", "Company-level financial profile."],
            ["Screener", "03_screener.py", "Filter and inspect companies."],
            ["Peers", "04_peers.py", "Compare companies with peer groups."],
            ["Trends", "05_trends.py", "Inspect financial trends over time."],
            ["Sectors", "06_sectors.py", "Analyze sector-level information."],
            [
                "Capital",
                "07_capital.py",
                "Review capital allocation and cash-flow information.",
            ],
            ["Reports", "08_reports.py", "Access generated reports and documents."],
        ],
        [1.1 * inch, 1.8 * inch, 4.0 * inch],
    )

    add_subtitle("Starting the dashboard")
    add_code("python -m streamlit run src/dashboard/app.py")

    add_body(
        "After starting Streamlit, use the navigation controls to move between "
        "screens. The dashboard reads analytical information from the SQLite "
        "database and generated report files."
    )

    story.append(PageBreak())

    # PAGE 4
    add_title("3. Home and Company Profile")
    add_subtitle("Home screen")
    add_body(
        "The Home screen is the starting point for the platform. It provides a "
        "high-level view of the analytical application and its available modules."
    )
    add_bullet("Use Home when first opening the dashboard.")
    add_bullet("Use the navigation menu to move into company and analytical screens.")
    add_bullet("Use the reports and analytics screens for deeper investigation.")

    add_subtitle("Company Profile screen")
    add_body(
        "The Profile screen is used for company-level investigation. An analyst "
        "can select a company and inspect information sourced from the company "
        "master data and related financial tables."
    )
    add_bullet("Company identity and descriptive information")
    add_bullet("Sector and industry classification")
    add_bullet("Financial history")
    add_bullet("Financial ratios")
    add_bullet("Valuation information")
    add_bullet("Peer information")
    add_bullet("Available company documents")

    add_subtitle("Analyst workflow")
    add_body(
        "A typical workflow is to begin with a company profile, inspect historical "
        "financials and ratios, then move to peers, trends and generated reports "
        "for additional context."
    )

    story.append(PageBreak())

    # PAGE 5
    add_title("4. Screener")
    add_body(
        "The Screener screen provides a structured way to narrow the company "
        "universe using financial criteria. The corresponding API endpoint is "
        "GET /api/v1/screener/."
    )

    add_subtitle("Available screening dimensions")
    add_bullet("Sector")
    add_bullet("Minimum return on equity")
    add_bullet("Maximum debt-to-equity")
    add_bullet("Minimum five-year revenue CAGR")
    add_bullet("Minimum operating profit margin")
    add_bullet("Minimum free cash flow")

    add_subtitle("Using the screener")
    add_body(
        "Select the desired filters, review the returned company set and then "
        "open individual companies in the Profile screen for detailed inspection."
    )

    add_subtitle("API equivalent")
    add_code('curl "http://127.0.0.1:8000/api/v1/screener/?min_roe=15"')

    add_body(
        "The screener should be treated as a filtering and exploration tool. "
        "Screening results reflect the data and criteria supplied to the platform "
        "and should be investigated further through the underlying financial data."
    )

    story.append(PageBreak())

    # PAGE 6
    add_title("5. Peer Comparison and Trends")
    add_subtitle("Peer Comparison")
    add_body(
        "The Peer Comparison screen uses the platform's peer-group information "
        "and percentile data. It is designed to provide relative context for "
        "company-level metrics."
    )
    add_bullet("Select a company.")
    add_bullet("Review its peer group.")
    add_bullet("Inspect available peer metrics and percentile information.")
    add_bullet("Use the company Profile screen for additional financial detail.")

    add_subtitle("Peer API")
    add_code("curl http://127.0.0.1:8000/api/v1/peers/BAJAJAUTO")

    add_subtitle("Trends")
    add_body(
        "The Trends screen is used to inspect financial changes across years. "
        "Historical information can help identify changes in profitability, "
        "growth, cash flow and other financial measures."
    )
    add_bullet("Compare historical periods rather than relying on a single year.")
    add_bullet("Look for changes in direction and consistency.")
    add_bullet("Use the underlying company financials to validate unusual movements.")

    story.append(PageBreak())

    # PAGE 7
    add_title("6. Sector Analysis and Capital Allocation")
    add_subtitle("Sector Analysis")
    add_body(
        "The Sector Analysis screen organizes companies by sector and provides "
        "sector-level analytical context."
    )
    add_bullet("Review the available sectors.")
    add_bullet("Select a sector for company-level inspection.")
    add_bullet("Use sector information to provide context around company metrics.")
    add_bullet("Cross-check sector results with individual company data.")

    add_subtitle("Sector API")
    add_code(
        "curl http://127.0.0.1:8000/api/v1/sectors/\n"
        "curl http://127.0.0.1:8000/api/v1/sectors/Financials"
    )

    add_subtitle("Capital Allocation")
    add_body(
        "The Capital Allocation screen focuses on cash-flow-related analytical "
        "information. The platform calculates metrics such as free cash flow, "
        "CFO/PAT ratio, CapEx intensity and related classifications."
    )
    add_bullet("Review operating cash generation.")
    add_bullet("Review free cash flow.")
    add_bullet("Inspect capital expenditure intensity.")
    add_bullet(
        "Consider the relationship between accounting profit and cash generation."
    )

    story.append(PageBreak())

    # PAGE 8
    add_title("7. Annual Reports and Generated Reports")
    add_subtitle("Annual Reports screen")
    add_body(
        "The Annual Reports screen provides access to available company documents "
        "stored in the documents dataset and generated reporting outputs."
    )
    add_bullet("Search or select the relevant company.")
    add_bullet("Review available document records.")
    add_bullet("Use generated company tearsheets for summarized financial analysis.")

    add_subtitle("Company tearsheets")
    add_body(
        "Company tearsheets are stored in reports/tearsheets. The repository "
        "contains generated tearsheets for the analytical company universe."
    )
    add_code("reports/tearsheets/<COMPANY_ID>_tearsheet.pdf")

    add_subtitle("Sector reports")
    add_code("reports/sector/<SECTOR>_report.pdf")

    add_subtitle("Portfolio report")
    add_code("reports/portfolio/portfolio_summary.pdf")

    add_body(
        "Reports provide a convenient presentation layer over the underlying "
        "analytical outputs. For detailed investigation, analysts should also "
        "inspect the database-backed dashboard and API responses."
    )

    story.append(PageBreak())

    # PAGE 9
    add_title("8. KMeans Clustering and Analytical Reports")
    add_body(
        "The clustering workflow groups companies using five financial features: "
        "return on equity, debt-to-equity, five-year revenue CAGR, five-year FCF "
        "CAGR and operating profit margin."
    )

    add_subtitle("Clustering workflow")
    add_bullet("Prepare the latest company-level analytical features.")
    add_bullet("Apply sector-median imputation where required.")
    add_bullet("Standardize the features.")
    add_bullet("Run KMeans with five clusters.")
    add_bullet("Calculate distance from the cluster centroid.")
    add_bullet("Profile and label the resulting clusters.")

    add_subtitle("Outputs")
    add_code(
        "output/cluster_labels.csv\n"
        "output/cluster_profiles.csv\n"
        "reports/elbow_plot.png\n"
        "reports/correlation_heatmap.png\n"
        "output/outlier_report.csv\n"
        "output/portfolio_stats.csv"
    )

    add_subtitle("Elbow plot")
    add_body(
        "The elbow plot records KMeans inertia across candidate cluster counts "
        "and is used as a diagnostic for the clustering workflow."
    )

    add_subtitle("Correlation heatmap")
    add_body(
        "The correlation heatmap provides Pearson correlation information for "
        "selected financial KPIs."
    )

    story.append(PageBreak())

    # PAGE 10
    add_title("9. FastAPI Analyst Guide")
    add_body(
        "The FastAPI service provides programmatic access to the platform's "
        "analytical data. Start the API from the project root."
    )

    add_code("uvicorn src.api.main:app --reload --port 8000")

    add_subtitle("Interactive API documentation")
    add_code("http://127.0.0.1:8000/docs")

    add_subtitle("Company examples")
    add_code(
        "curl http://127.0.0.1:8000/api/v1/companies/\n"
        "curl http://127.0.0.1:8000/api/v1/companies/RELIANCE\n"
        "curl http://127.0.0.1:8000/api/v1/companies/RELIANCE/financials\n"
        "curl http://127.0.0.1:8000/api/v1/companies/RELIANCE/ratios\n"
        "curl http://127.0.0.1:8000/api/v1/companies/RELIANCE/valuation\n"
        "curl http://127.0.0.1:8000/api/v1/companies/RELIANCE/peers\n"
        "curl http://127.0.0.1:8000/api/v1/companies/RELIANCE/documents"
    )

    add_subtitle("Portfolio and documents")
    add_code(
        "curl http://127.0.0.1:8000/api/v1/portfolio/stats\n"
        "curl http://127.0.0.1:8000/api/v1/documents/"
    )

    story.append(PageBreak())

    # PAGE 11
    add_title("10. API Health, OpenAPI and Postman")
    add_subtitle("Health checks")
    add_code(
        "curl http://127.0.0.1:8000/api/v1/health/\n"
        "curl http://127.0.0.1:8000/api/v1/system/health"
    )

    add_body(
        "The system health endpoint provides API and database status information "
        "including table-level row counts and uptime information."
    )

    add_subtitle("OpenAPI")
    add_body(
        "The generated OpenAPI specification is stored at reports/openapi.json. "
        "The same specification is available interactively from the running "
        "FastAPI application's documentation."
    )
    add_code("reports/openapi.json")

    add_subtitle("Postman")
    add_body(
        "A Postman collection containing the API requests is available for "
        "manual endpoint testing."
    )
    add_code("reports/postman_collection.json")

    add_subtitle("Recommended API validation flow")
    add_bullet("Start the FastAPI server.")
    add_bullet("Open /docs.")
    add_bullet("Check the health endpoint.")
    add_bullet("Test the company endpoint.")
    add_bullet("Test the screener.")
    add_bullet("Test portfolio statistics.")
    add_bullet("Use Postman for repeated endpoint checks.")

    story.append(PageBreak())

    # PAGE 12
    add_title("11. Testing and Troubleshooting")
    add_subtitle("Full test suite")
    add_code("pytest -q")

    add_subtitle("Targeted tests")
    add_code(
        "pytest tests/test_api.py -q\n"
        "pytest tests/test_integration.py -q\n"
        "pytest tests/test_dashboard.py -q\n"
        "pytest tests/test_performance.py -q -s"
    )

    add_subtitle("Common troubleshooting")
    add_bullet(
        "If the dashboard does not start, use "
        "'python -m streamlit run src/dashboard/app.py'."
    )
    add_bullet(
        "If FastAPI imports fail, activate .venv and start Uvicorn from the project root."
    )
    add_bullet("If database errors occur, verify that data/nifty100.db exists.")
    add_bullet(
        "If a test fails, run that test file separately before running the full suite."
    )
    add_bullet(
        "If an API endpoint returns unexpected data, inspect /docs and the corresponding router."
    )

    add_subtitle("Performance validation")
    add_code(
        "pytest tests/test_performance.py -q -s\n"
        "python src/performance/check_query_plans.py"
    )

    add_body(
        "The performance suite covers repeated API calls, concurrent API calls "
        "and representative SQLite queries. SQLite indexes are used for commonly "
        "queried company, year, peer and document fields."
    )

    story.append(PageBreak())

    # PAGE 13
    add_title("12. Analyst Workflow Checklist")
    add_body(
        "The following workflow provides a repeatable approach for exploring a "
        "company or a group of companies through the platform."
    )

    checklist = [
        ["Step", "Action"],
        ["1", "Start the Streamlit dashboard."],
        ["2", "Open the Home screen and review the available modules."],
        ["3", "Select a company in Profile."],
        ["4", "Review financial history and ratios."],
        ["5", "Inspect valuation information."],
        ["6", "Review peer information."],
        ["7", "Use Trends to inspect historical changes."],
        ["8", "Use the Screener for structured filtering."],
        ["9", "Use Sector Analysis for sector context."],
        ["10", "Review Capital Allocation and cash-flow information."],
        ["11", "Open Annual Reports and company tearsheets."],
        ["12", "Use FastAPI when programmatic access is required."],
        ["13", "Validate results with the underlying database-backed outputs."],
    ]

    add_table(checklist, [0.6 * inch, 6.3 * inch])

    add_subtitle("Analytical caution")
    add_body(
        "Dashboard filters, rankings, clusters and financial metrics are derived "
        "from the platform's datasets and analytical rules. Results should be "
        "interpreted together with their underlying financial context rather than "
        "as standalone conclusions."
    )

    story.append(PageBreak())

    # PAGE 14
    add_title("13. Project Reference Map")
    add_body(
        "The following locations are useful when maintaining or extending the platform."
    )

    add_table(
        [
            ["Location", "Purpose"],
            ["src/etl/", "Data loading, normalization and validation."],
            ["src/analytics/", "Financial KPI and analytical calculations."],
            ["src/api/", "FastAPI application and routers."],
            ["src/dashboard/", "Streamlit application and pages."],
            ["src/performance/", "Database indexes and query-plan checks."],
            ["tests/", "Automated regression and integration tests."],
            ["data/nifty100.db", "Main analytical SQLite database."],
            ["output/", "Machine-readable analytical outputs."],
            ["reports/", "Visualizations, API specifications and generated reports."],
            ["docs/", "Project documentation and analyst guide."],
        ],
        [1.7 * inch, 5.2 * inch],
    )

    add_subtitle("Useful commands")
    add_code(
        "python -m streamlit run src/dashboard/app.py\n"
        "uvicorn src.api.main:app --reload --port 8000\n"
        "pytest -q\n"
        "git status"
    )

    add_body(
        "This guide is intended as a practical reference for analysts and "
        "developers working with the NIFTY 100 Financial Intelligence Platform."
    )

    document.build(story)
    print(f"Analyst guide created: {OUTPUT}")
    print("Pages: 14")


if __name__ == "__main__":
    build_analyst_guide()
