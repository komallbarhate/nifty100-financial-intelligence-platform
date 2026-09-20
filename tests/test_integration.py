import sqlite3

from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)

DB_PATH = "data/nifty100.db"


def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


# ---------------------------------------------------------------------------
# COMPANY COUNT CONSISTENCY
# ---------------------------------------------------------------------------

def test_company_count_matches_database():
    connection = get_db_connection()

    try:
        cursor = connection.execute(
            "SELECT COUNT(*) AS count FROM companies"
        )
        db_count = cursor.fetchone()["count"]
    finally:
        connection.close()

    response = client.get("/api/v1/companies/")

    assert response.status_code == 200

    api_count = response.json()["count"]

    assert api_count == db_count
    assert api_count == 92


# ---------------------------------------------------------------------------
# SECTOR COUNT CONSISTENCY
# ---------------------------------------------------------------------------

def test_sector_count_matches_database():
    connection = get_db_connection()

    try:
        cursor = connection.execute(
            "SELECT COUNT(DISTINCT sector) AS count FROM sectors"
        )
        db_count = cursor.fetchone()["count"]
    finally:
        connection.close()

    response = client.get("/api/v1/sectors/")

    assert response.status_code == 200

    api_count = response.json()["count"]

    assert api_count == db_count


# ---------------------------------------------------------------------------
# FINANCIAL RATIOS CONSISTENCY
# ---------------------------------------------------------------------------

def test_reliance_ratio_count_matches_database():
    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM financial_ratios
            WHERE company_id = ?
            """,
            ("RELIANCE",),
        )
        db_count = cursor.fetchone()["count"]
    finally:
        connection.close()

    response = client.get("/api/v1/companies/RELIANCE/ratios")

    assert response.status_code == 200

    api_data = response.json()

    assert api_data["count"] == db_count
    assert len(api_data["ratios"]) == db_count


# ---------------------------------------------------------------------------
# FINANCIALS CONSISTENCY
# ---------------------------------------------------------------------------

def test_reliance_financials_count_matches_database():
    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM profitandloss
            WHERE company_id = ?
            """,
            ("RELIANCE",),
        )
        db_count = cursor.fetchone()["count"]
    finally:
        connection.close()

    response = client.get("/api/v1/companies/RELIANCE/financials")

    assert response.status_code == 200

    api_data = response.json()

    assert api_data["count"] == db_count
    assert len(api_data["financials"]) == db_count


# ---------------------------------------------------------------------------
# MARKET CAP CONSISTENCY
# ---------------------------------------------------------------------------

def test_reliance_market_cap_count_matches_database():
    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM market_cap
            WHERE company_id = ?
            """,
            ("RELIANCE",),
        )
        db_count = cursor.fetchone()["count"]
    finally:
        connection.close()

    response = client.get(
        "/api/v1/valuation/market-cap/RELIANCE"
    )

    assert response.status_code == 200

    api_data = response.json()

    assert api_data["count"] == db_count
    assert len(api_data["history"]) == db_count


# ---------------------------------------------------------------------------
# DOCUMENT COUNT CONSISTENCY
# ---------------------------------------------------------------------------

def test_reliance_document_count_matches_database():
    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM documents
            WHERE company_id = ?
            """,
            ("RELIANCE",),
        )
        db_count = cursor.fetchone()["count"]
    finally:
        connection.close()

    response = client.get(
        "/api/v1/documents/",
        params={"company_id": "RELIANCE"},
    )

    assert response.status_code == 200

    api_data = response.json()

    assert api_data["count"] == db_count
    assert len(api_data["documents"]) == db_count


# ---------------------------------------------------------------------------
# PEER CONSISTENCY
# ---------------------------------------------------------------------------

def test_bajaj_auto_peer_count_matches_database():
    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            SELECT peer_group
            FROM peer_groups
            WHERE company_id = ?
            LIMIT 1
            """,
            ("BAJAJAUTO",),
        )

        row = cursor.fetchone()

        assert row is not None

        peer_group = row["peer_group"]

        cursor = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM peer_groups
            WHERE peer_group = ?
            """,
            (peer_group,),
        )

        db_count = cursor.fetchone()["count"]
    finally:
        connection.close()

    response = client.get("/api/v1/peers/BAJAJAUTO")

    assert response.status_code == 200

    api_data = response.json()

    assert api_data["company_id"] == "BAJAJAUTO"
    assert api_data["peer_group"] == peer_group
    assert api_data["count"] == db_count


# ---------------------------------------------------------------------------
# DATABASE COMPANY IDs VS API
# ---------------------------------------------------------------------------

def test_database_company_ids_exist_in_api():
    connection = get_db_connection()

    try:
        rows = connection.execute(
            "SELECT id FROM companies ORDER BY id"
        ).fetchall()

        db_company_ids = [row["id"] for row in rows]
    finally:
        connection.close()

    response = client.get("/api/v1/companies/")

    assert response.status_code == 200

    api_company_ids = sorted(
        row["company_id"]
        for row in response.json()["companies"]
    )

    assert api_company_ids == db_company_ids


# ---------------------------------------------------------------------------
# API OPENAPI DOCUMENTATION
# ---------------------------------------------------------------------------

def test_documented_endpoints_are_reachable():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    required_paths = [
        "/api/v1/companies/",
        "/api/v1/companies/{company_id}",
        "/api/v1/companies/{company_id}/financials",
        "/api/v1/companies/{company_id}/ratios",
        "/api/v1/companies/{company_id}/valuation",
        "/api/v1/companies/{company_id}/peers",
        "/api/v1/companies/{company_id}/documents",
        "/api/v1/screener/",
        "/api/v1/sectors/",
        "/api/v1/sectors/{sector_name}",
        "/api/v1/sectors/{sector_name}/summary",
        "/api/v1/peers/{company_id}",
        "/api/v1/valuation/market-cap",
        "/api/v1/valuation/market-cap/{company_id}",
        "/api/v1/portfolio/stats",
        "/api/v1/documents/",
        "/api/v1/health/",
        "/api/v1/system/health",
    ]

    for path in required_paths:
        assert path in paths