# Sprint 6 - Day 43 Performance Report

## 1. Objective

Validate API performance, concurrent request handling, SQLite query performance,
dashboard startup, and database indexing for the NIFTY 100 Financial Intelligence Platform.

---

## 2. API Performance Results

### Repeated Health Requests

- Requests: 20
- Average latency: 9.55 ms
- P95 latency: 12.98 ms
- Maximum latency: 13.69 ms
- Result: PASS

### Concurrent Health Requests

- Requests: 20
- Concurrent workers: 10
- Successful requests: 20/20
- Average latency: 59.56 ms
- Maximum latency: 77.97 ms
- Result: PASS

### Concurrent Company Requests

- Requests: 10
- Concurrent workers: 10
- Successful requests: 10/10
- Average latency: 51.22 ms
- Maximum latency: 63.61 ms
- Result: PASS

### SQLite Representative Query

- Query runs: 20
- Rows returned: 100
- Average execution time: 1.81 ms
- Maximum execution time: 3.64 ms
- Result: PASS

---

## 3. Database Indexing

### Index Count

Before Day 43:

- 4 existing indexes

After Day 43:

- 11 total indexes

Seven API-focused indexes were added or confirmed:

1. `idx_financial_ratios_company_year`
2. `idx_financial_ratios_year`
3. `idx_market_cap_company_year`
4. `idx_documents_company_year`
5. `idx_sectors_company`
6. `idx_peer_groups_company`
7. `idx_peer_percentiles_company_group_year`

The index creation script uses `IF NOT EXISTS`, making it safe to run repeatedly.

---

## 4. SQLite Query Plan Verification

SQLite `EXPLAIN QUERY PLAN` confirmed index usage for all representative API queries.

### Financial Ratios by Company

Uses:

`idx_financial_ratios_company_year`

### Financial Ratios by Year

Uses:

`idx_financial_ratios_year`

### Market Cap by Company

Uses:

`idx_market_cap_company_year`

### Documents by Company

Uses:

`idx_documents_company_year`

### Peer Groups by Company

Uses:

`idx_peer_groups_company`

### Peer Percentiles by Company, Peer Group and Year

Uses:

`idx_peer_percentiles_company_group_year`

Result:

**All six representative query plans confirmed index usage.**

---

## 5. Dashboard Smoke and E2E Testing

Dashboard tests completed successfully.

- Dashboard directory validation: PASS
- All 8 dashboard pages present: PASS
- Dashboard Python compilation: PASS
- Streamlit application startup: PASS
- Company metric validation: PASS
- Financial year metric validation: PASS
- Peer-group metric validation: PASS
- Dashboard success message: PASS

Dashboard test result:

**8 passed**

---

## 6. Full Regression Test

After adding the Day 43 performance, indexing, and dashboard tests:

**188 passed, 0 failed, 0 skipped**

Runtime:

**12.14 seconds**

Two dependency deprecation warnings were reported by FastAPI/Starlette TestClient.
They did not cause test failures.

---

## 7. Day 43 Conclusion

Day 43 performance and quality validation completed successfully.

Validated areas:

- API response latency
- Repeated API requests
- Concurrent API requests
- SQLite query performance
- Database index usage
- Streamlit dashboard startup
- Dashboard page availability
- Dashboard metrics
- Full regression suite

Overall Day 43 result:

**PASS — 188 automated tests passed with zero failures.**