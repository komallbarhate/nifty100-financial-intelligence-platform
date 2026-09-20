"""
Sprint 6 - Day 43
API performance and concurrency tests.

These tests measure:
- API response latency
- repeated requests
- concurrent requests
- important endpoint availability
- database query performance
"""

import sqlite3
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

BASE_URL = "/api/v1"


def measure_request(method, path, **kwargs):
    """Measure one API request and return status and elapsed milliseconds."""

    start = time.perf_counter()

    response = client.request(
        method,
        path,
        **kwargs,
    )

    elapsed_ms = (time.perf_counter() - start) * 1000

    return response.status_code, elapsed_ms


def test_health_endpoint_performance():
    """Health endpoint should respond quickly."""

    status_code, elapsed_ms = measure_request(
        "GET",
        f"{BASE_URL}/health/",
    )

    assert status_code == 200
    assert elapsed_ms < 1000


def test_company_list_performance():
    """Company list endpoint should respond within one second."""

    status_code, elapsed_ms = measure_request(
        "GET",
        f"{BASE_URL}/companies/",
    )

    assert status_code == 200
    assert elapsed_ms < 1000


def test_screener_performance():
    """Base screener request should respond within one second."""

    status_code, elapsed_ms = measure_request(
        "GET",
        f"{BASE_URL}/screener/",
    )

    assert status_code == 200
    assert elapsed_ms < 1000


def test_sector_list_performance():
    """Sector list endpoint should respond within one second."""

    status_code, elapsed_ms = measure_request(
        "GET",
        f"{BASE_URL}/sectors/",
    )

    assert status_code == 200
    assert elapsed_ms < 1000


def test_market_cap_performance():
    """Market-cap endpoint should respond within one second."""

    status_code, elapsed_ms = measure_request(
        "GET",
        f"{BASE_URL}/valuation/market-cap",
    )

    assert status_code == 200
    assert elapsed_ms < 1000


def test_portfolio_stats_performance():
    """Portfolio statistics endpoint should respond within one second."""

    status_code, elapsed_ms = measure_request(
        "GET",
        f"{BASE_URL}/portfolio/stats",
    )

    assert status_code == 200
    assert elapsed_ms < 1000


def test_repeated_health_requests():
    """Measure repeated health requests and keep the latency stable."""

    timings = []

    for _ in range(20):
        status_code, elapsed_ms = measure_request(
            "GET",
            f"{BASE_URL}/health/",
        )

        assert status_code == 200
        timings.append(elapsed_ms)

    average_ms = statistics.mean(timings)
    p95_ms = sorted(timings)[int(len(timings) * 0.95) - 1]

    print()
    print("Repeated health requests")
    print(f"Requests: {len(timings)}")
    print(f"Average: {average_ms:.2f} ms")
    print(f"P95: {p95_ms:.2f} ms")
    print(f"Maximum: {max(timings):.2f} ms")

    assert average_ms < 1000


def test_concurrent_health_requests():
    """Verify that concurrent API requests complete successfully."""

    request_count = 20

    def make_request(_):
        return measure_request(
            "GET",
            f"{BASE_URL}/health/",
        )

    with ThreadPoolExecutor(
        max_workers=10,
    ) as executor:

        results = list(
            executor.map(
                make_request,
                range(request_count),
            )
        )

    status_codes = [result[0] for result in results]

    timings = [result[1] for result in results]

    successful = status_codes.count(200)

    average_ms = statistics.mean(timings)

    print()
    print("Concurrent health requests")
    print(f"Requests: {request_count}")
    print(f"Successful: {successful}")
    print(f"Average: {average_ms:.2f} ms")
    print(f"Maximum: {max(timings):.2f} ms")

    assert successful == request_count
    assert average_ms < 2000


def test_concurrent_company_requests():
    """Verify concurrent company requests."""

    company_ids = [
        "RELIANCE",
        "TCS",
        "INFY",
        "HDFCBANK",
        "ICICIBANK",
        "SBIN",
        "ITC",
        "LT",
        "MARUTI",
        "TITAN",
    ]

    def make_request(company_id):
        return measure_request(
            "GET",
            f"{BASE_URL}/companies/{company_id}",
        )

    with ThreadPoolExecutor(
        max_workers=10,
    ) as executor:

        results = list(
            executor.map(
                make_request,
                company_ids,
            )
        )

    status_codes = [result[0] for result in results]

    timings = [result[1] for result in results]

    print()
    print("Concurrent company requests")
    print(f"Requests: {len(company_ids)}")
    print(f"Successful: {status_codes.count(200)}")
    print(f"Average: " f"{statistics.mean(timings):.2f} ms")
    print(f"Maximum: " f"{max(timings):.2f} ms")

    assert all(status_code == 200 for status_code in status_codes)


def test_database_query_performance():
    """Verify a representative SQLite query completes quickly."""

    db_path = Path(__file__).resolve().parents[1] / "data" / "nifty100.db"

    assert db_path.exists()

    timings = []

    with sqlite3.connect(db_path) as conn:

        for _ in range(20):

            start = time.perf_counter()

            rows = conn.execute("""
                SELECT
                    company_id,
                    year,
                    return_on_equity_pct,
                    debt_to_equity,
                    revenue_cagr_5yr,
                    operating_profit_margin_pct
                FROM financial_ratios
                ORDER BY year DESC
                LIMIT 100
                """).fetchall()

            elapsed_ms = (time.perf_counter() - start) * 1000

            timings.append(elapsed_ms)

    assert len(rows) > 0

    average_ms = statistics.mean(timings)

    print()
    print("SQLite representative query")
    print(f"Runs: {len(timings)}")
    print(f"Rows returned: {len(rows)}")
    print(f"Average: {average_ms:.2f} ms")
    print(f"Maximum: {max(timings):.2f} ms")

    assert average_ms < 1000
