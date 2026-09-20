-- NIFTY 100 Financial Intelligence Platform
-- Exploratory SQL Queries
-- Purpose: row counts, null checks, year coverage, duplicates,
-- and basic data validation.

-- Q01: Row counts for all core tables
SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL
SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL
SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL
SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL
SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL
SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL
SELECT 'market_cap', COUNT(*) FROM market_cap
UNION ALL
SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL
SELECT 'peer_groups', COUNT(*) FROM peer_groups
UNION ALL
SELECT 'peer_percentiles', COUNT(*) FROM peer_percentiles
UNION ALL
SELECT 'documents', COUNT(*) FROM documents;


-- Q02: Null checks in the companies master
SELECT
    COUNT(*) AS total_companies,
    SUM(CASE WHEN id IS NULL OR TRIM(id) = '' THEN 1 ELSE 0 END) AS null_company_ids,
    SUM(CASE WHEN company_name IS NULL OR TRIM(company_name) = '' THEN 1 ELSE 0 END) AS null_company_names
FROM companies;


-- Q03: Year distribution for Profit & Loss
SELECT
    year,
    COUNT(*) AS row_count
FROM profitandloss
GROUP BY year
ORDER BY year;


-- Q04: Year distribution for Balance Sheet
SELECT
    year,
    COUNT(*) AS row_count
FROM balancesheet
GROUP BY year
ORDER BY year;


-- Q05: Year distribution for Cash Flow
SELECT
    year,
    COUNT(*) AS row_count
FROM cashflow
GROUP BY year
ORDER BY year;


-- Q06: Profit & Loss coverage by company
SELECT
    company_id,
    MIN(year) AS first_year,
    MAX(year) AS last_year,
    COUNT(DISTINCT year) AS years_available
FROM profitandloss
GROUP BY company_id
ORDER BY years_available, company_id;


-- Q07: Balance Sheet coverage by company
SELECT
    company_id,
    MIN(year) AS first_year,
    MAX(year) AS last_year,
    COUNT(DISTINCT year) AS years_available
FROM balancesheet
GROUP BY company_id
ORDER BY years_available, company_id;


-- Q08: Cash Flow coverage by company
SELECT
    company_id,
    MIN(year) AS first_year,
    MAX(year) AS last_year,
    COUNT(DISTINCT year) AS years_available
FROM cashflow
GROUP BY company_id
ORDER BY years_available, company_id;


-- Q09: Duplicate company-year records in Profit & Loss
SELECT
    'profitandloss' AS table_name,
    company_id,
    year,
    COUNT(*) AS duplicate_count
FROM profitandloss
GROUP BY company_id, year
HAVING COUNT(*) > 1

UNION ALL

SELECT
    'balancesheet' AS table_name,
    company_id,
    year,
    COUNT(*) AS duplicate_count
FROM balancesheet
GROUP BY company_id, year
HAVING COUNT(*) > 1;


-- Q10: Financial ratio coverage by company
SELECT
    company_id,
    MIN(year) AS first_year,
    MAX(year) AS last_year,
    COUNT(DISTINCT year) AS years_available
FROM financial_ratios
GROUP BY company_id
ORDER BY years_available, company_id;


-- Q11: Latest financial ratio year
SELECT
    MAX(year) AS latest_ratio_year
FROM financial_ratios;


-- Q12: Companies missing from the sector master
SELECT
    c.id AS company_id,
    c.company_name
FROM companies c
LEFT JOIN sectors s
    ON c.id = s.company_id
WHERE s.company_id IS NULL
ORDER BY c.id;


-- Q13: Companies missing financial ratios
SELECT
    c.id AS company_id,
    c.company_name
FROM companies c
LEFT JOIN financial_ratios r
    ON c.id = r.company_id
WHERE r.company_id IS NULL
ORDER BY c.id;


-- Q14: Financial ratio null coverage for important KPIs
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN return_on_equity_pct IS NULL THEN 1 ELSE 0 END) AS null_roe,
    SUM(CASE WHEN debt_to_equity IS NULL THEN 1 ELSE 0 END) AS null_debt_to_equity,
    SUM(CASE WHEN operating_profit_margin_pct IS NULL THEN 1 ELSE 0 END) AS null_opm,
    SUM(CASE WHEN revenue_cagr_5yr IS NULL THEN 1 ELSE 0 END) AS null_revenue_cagr_5yr,
    SUM(CASE WHEN free_cash_flow_cr IS NULL THEN 1 ELSE 0 END) AS null_fcf
FROM financial_ratios;


-- Q15: Companies with the longest Profit & Loss history
SELECT
    company_id,
    MIN(year) AS first_year,
    MAX(year) AS last_year,
    COUNT(DISTINCT year) AS years_available
FROM profitandloss
GROUP BY company_id
ORDER BY years_available DESC, company_id
LIMIT 20;