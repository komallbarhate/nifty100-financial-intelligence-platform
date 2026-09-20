from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


# ---------------------------------------------------------------------------
# BASIC API / HEALTH
# ---------------------------------------------------------------------------

def test_root():
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "NIFTY 100 Financial Intelligence Platform API"
    assert data["version"] == "1.0.0"
    assert data["status"] == "online"
    assert data["docs"] == "/docs"


def test_api_root():
    response = client.get("/api/v1")
    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)


def test_health():
    response = client.get("/api/v1/health/")
    assert response.status_code == 200

    data = response.json()

    assert "status" in data
    assert "database" in data
    assert "uptime_seconds" in data
    assert "version" in data


def test_system_health():
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "database" in data
    assert "uptime_seconds" in data
    assert "checked_at" in data


# ---------------------------------------------------------------------------
# COMPANIES
# ---------------------------------------------------------------------------

def test_list_companies():
    response = client.get("/api/v1/companies/")
    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 92
    assert isinstance(data["companies"], list)
    assert len(data["companies"]) == 92

    first = data["companies"][0]

    assert "company_id" in first
    assert "company_name" in first
    assert "sector" in first
    assert "industry" in first


def test_get_company():
    response = client.get("/api/v1/companies/RELIANCE")
    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "RELIANCE"
    assert "company_name" in data
    assert "sector" in data
    assert "industry" in data


def test_get_company_not_found():
    response = client.get("/api/v1/companies/DOESNOTEXIST")
    assert response.status_code == 404


def test_company_financials():
    response = client.get("/api/v1/companies/RELIANCE/financials")
    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "RELIANCE"
    assert data["count"] > 0
    assert isinstance(data["financials"], list)
    assert len(data["financials"]) == data["count"]

    row = data["financials"][0]

    assert row["company_id"] == "RELIANCE"
    assert "year" in row


def test_company_ratios():
    response = client.get("/api/v1/companies/RELIANCE/ratios")
    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "RELIANCE"
    assert data["count"] > 0
    assert isinstance(data["ratios"], list)
    assert len(data["ratios"]) == data["count"]

    row = data["ratios"][0]

    assert row["company_id"] == "RELIANCE"
    assert "year" in row


def test_company_valuation():
    response = client.get("/api/v1/companies/RELIANCE/valuation")
    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "RELIANCE"
    assert data["count"] > 0
    assert isinstance(data["valuation"], list)
    assert len(data["valuation"]) == data["count"]

    row = data["valuation"][0]

    assert row["company_id"] == "RELIANCE"
    assert "year" in row


def test_company_peers():
    response = client.get("/api/v1/companies/BAJAJAUTO/peers")
    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "BAJAJAUTO"
    assert data["count"] > 0
    assert isinstance(data["peers"], list)
    assert len(data["peers"]) == data["count"]


def test_company_documents():
    response = client.get("/api/v1/companies/RELIANCE/documents")
    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "RELIANCE"
    assert data["count"] > 0
    assert isinstance(data["documents"], list)
    assert len(data["documents"]) == data["count"]


# ---------------------------------------------------------------------------
# SCREENER
# ---------------------------------------------------------------------------

def test_screener():
    response = client.get("/api/v1/screener/")
    assert response.status_code == 200

    data = response.json()

    assert data["count"] > 0
    assert isinstance(data["results"], list)
    assert len(data["results"]) == data["count"]

    row = data["results"][0]

    assert "company_id" in row
    assert "company_name" in row


def test_screener_sector_filter():
    response = client.get(
        "/api/v1/screener/",
        params={"sector": "Information Technology"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["filters"]["sector"] == "Information Technology"
    assert isinstance(data["results"], list)

    for row in data["results"]:
        assert row["sector"] == "Information Technology"


def test_screener_roe_filter():
    response = client.get(
        "/api/v1/screener/",
        params={"min_roe": 10},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["filters"]["min_roe"] == 10
    assert isinstance(data["results"], list)

    for row in data["results"]:
        if row.get("return_on_equity_pct") is not None:
            assert row["return_on_equity_pct"] >= 10


# ---------------------------------------------------------------------------
# SECTORS
# ---------------------------------------------------------------------------

def test_list_sectors():
    response = client.get("/api/v1/sectors/")
    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 10
    assert isinstance(data["sectors"], list)
    assert len(data["sectors"]) == data["count"]


def test_sector_detail():
    response = client.get("/api/v1/sectors/Information%20Technology")
    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)


def test_sector_summary():
    response = client.get(
        "/api/v1/sectors/Information%20Technology/summary"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# PEERS
# ---------------------------------------------------------------------------

def test_peer_comparison():
    response = client.get("/api/v1/peers/BAJAJAUTO")
    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "BAJAJAUTO"
    assert "peer_group" in data
    assert "peers" in data


def test_peer_comparison_missing_company():
    response = client.get("/api/v1/peers/DOESNOTEXIST")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# VALUATION
# ---------------------------------------------------------------------------

def test_market_cap():
    response = client.get("/api/v1/valuation/market-cap")
    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 552
    assert isinstance(data["results"], list)
    assert len(data["results"]) == data["count"]


def test_company_market_cap():
    response = client.get("/api/v1/valuation/market-cap/RELIANCE")
    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "RELIANCE"
    assert data["count"] > 0
    assert isinstance(data["history"], list)
    assert len(data["history"]) == data["count"]


# ---------------------------------------------------------------------------
# PORTFOLIO
# ---------------------------------------------------------------------------

def test_portfolio_stats():
    response = client.get("/api/v1/portfolio/stats")
    assert response.status_code == 200

    data = response.json()

    assert data["count"] > 0
    assert isinstance(data["statistics"], list)
    assert len(data["statistics"]) == data["count"]


# ---------------------------------------------------------------------------
# DOCUMENTS
# ---------------------------------------------------------------------------

def test_documents():
    response = client.get("/api/v1/documents/")
    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1585
    assert isinstance(data["documents"], list)
    assert len(data["documents"]) == data["count"]


def test_documents_company_filter():
    response = client.get(
        "/api/v1/documents/",
        params={"company_id": "RELIANCE"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] > 0
    assert isinstance(data["documents"], list)

    for row in data["documents"]:
        assert row["company_id"] == "RELIANCE"


# ---------------------------------------------------------------------------
# OPENAPI
# ---------------------------------------------------------------------------

def test_openapi():
    response = client.get("/openapi.json")
    assert response.status_code == 200

    data = response.json()

    assert data["openapi"].startswith("3.")
    assert (
        data["info"]["title"]
        == "NIFTY 100 Financial Intelligence Platform API"
    )

    paths = data["paths"]

    assert "/api/v1/companies/" in paths
    assert "/api/v1/screener/" in paths
    assert "/api/v1/sectors/" in paths
    assert "/api/v1/peers/{company_id}" in paths
    assert "/api/v1/valuation/market-cap" in paths
    assert "/api/v1/portfolio/stats" in paths
    assert "/api/v1/documents/" in paths
    assert "/api/v1/health/" in paths