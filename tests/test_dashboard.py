"""
Sprint 6 - Day 43
Streamlit dashboard smoke and E2E tests.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest


BASE_DIR = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = BASE_DIR / "src" / "dashboard"

EXPECTED_PAGES = [
    "01_home.py",
    "02_profile.py",
    "03_screener.py",
    "04_peers.py",
    "05_trends.py",
    "06_sectors.py",
    "07_capital.py",
    "08_reports.py",
]


def test_dashboard_directory_exists():
    """Dashboard directory must exist."""

    assert DASHBOARD_DIR.exists()
    assert DASHBOARD_DIR.is_dir()


def test_all_dashboard_pages_exist():
    """All planned dashboard pages must exist."""

    for page in EXPECTED_PAGES:
        page_path = DASHBOARD_DIR / "pages" / page

        assert page_path.exists(), (
            f"Missing dashboard page: {page}"
        )


def test_dashboard_python_files_compile():
    """All dashboard Python files must compile."""

    python_files = list(
        DASHBOARD_DIR.rglob("*.py")
    )

    assert python_files

    for file_path in python_files:

        source = file_path.read_text(
            encoding="utf-8-sig"
        )

        compile(
            source,
            str(file_path),
            "exec",
        )


def test_dashboard_smoke():
    """Main Streamlit dashboard must start successfully."""

    app_path = DASHBOARD_DIR / "app.py"

    assert app_path.exists()

    app = AppTest.from_file(
        str(app_path)
    ).run(
        timeout=30
    )

    assert not app.exception

    assert len(app.title) >= 1

    titles = [
        element.value
        for element in app.title
    ]

    assert any(
        "Nifty 100" in title
        for title in titles
    )


def test_dashboard_company_metric():
    """Dashboard should display the expected company count."""

    app_path = DASHBOARD_DIR / "app.py"

    app = AppTest.from_file(
        str(app_path)
    ).run(
        timeout=30
    )

    assert not app.exception

    metric_values = [
        metric.value
        for metric in app.metric
    ]

    assert "92" in metric_values


def test_dashboard_year_metric():
    """Dashboard should display the financial year range."""

    app_path = DASHBOARD_DIR / "app.py"

    app = AppTest.from_file(
        str(app_path)
    ).run(
        timeout=30
    )

    assert not app.exception

    metric_values = [
        metric.value
        for metric in app.metric
    ]

    assert "2011–2024" in metric_values


def test_dashboard_peer_group_metric():
    """Dashboard should display the peer-group count."""

    app_path = DASHBOARD_DIR / "app.py"

    app = AppTest.from_file(
        str(app_path)
    ).run(
        timeout=30
    )

    assert not app.exception

    metric_values = [
        metric.value
        for metric in app.metric
    ]

    assert "11" in metric_values


def test_dashboard_success_message():
    """Dashboard should render its success/status message."""

    app_path = DASHBOARD_DIR / "app.py"

    app = AppTest.from_file(
        str(app_path)
    ).run(
        timeout=30
    )

    assert not app.exception

    assert len(app.success) >= 1