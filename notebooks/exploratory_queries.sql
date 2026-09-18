-- ============================================================
-- NIFTY 100 EXPLORATORY SQL QUERIES
-- SPRINT 1 - DAY 7
-- ============================================================

-- Q1. COMPANY COUNT
SELECT COUNT(*) AS total_companies
FROM companies;


-- Q2. FINANCIAL DATA COVERAGE
SELECT
    COUNT(DISTINCT company_id) AS companies_with_pnl,
    COUNT(DISTINCT year) AS years_available,
    MIN(year) AS first_year,
    MAX(year) AS last_year
FROM profitandloss;


-- Q3. TOP 10 COMPANIES BY 2024 SALES
SELECT
    company_id,
    sales
FROM profitandloss
WHERE year = 2024
ORDER BY sales DESC
LIMIT 10;


-- Q4. TOP 10 COMPANIES BY 2024 NET PROFIT
SELECT
    company_id,
    net_profit
FROM profitandloss
WHERE year = 2024
ORDER BY net_profit DESC
LIMIT 10;


-- Q5. 2024 PROFITABILITY
SELECT
    company_id,
    sales,
    operating_profit,
    net_profit,
    opm_percentage
FROM profitandloss
WHERE year = 2024
ORDER BY net_profit DESC
LIMIT 10;


-- Q6. COMPANY YEAR COVERAGE
SELECT
    company_id,
    COUNT(DISTINCT year) AS years_available,
    MIN(year) AS first_year,
    MAX(year) AS last_year
FROM profitandloss
GROUP BY company_id
ORDER BY years_available, company_id;


-- Q7. COMPANIES WITH LIMITED COVERAGE
SELECT
    company_id,
    COUNT(DISTINCT year) AS years_available,
    MIN(year) AS first_year,
    MAX(year) AS last_year
FROM profitandloss
GROUP BY company_id
HAVING COUNT(DISTINCT year) < 5
ORDER BY years_available;


-- Q8. SECTOR DISTRIBUTION
SELECT
    sector,
    COUNT(*) AS company_count
FROM sectors
GROUP BY sector
ORDER BY company_count DESC;


-- Q9. MARKET CAP DATA COVERAGE
SELECT
    COUNT(*) AS rows,
    COUNT(DISTINCT company_id) AS companies,
    MIN(date) AS first_date,
    MAX(date) AS last_date
FROM market_cap;


-- Q10. STOCK PRICE DATA COVERAGE
SELECT
    COUNT(*) AS rows,
    COUNT(DISTINCT company_id) AS companies,
    MIN(date) AS first_date,
    MAX(date) AS last_date
FROM stock_prices;


-- Q11. 2024 NET PROFIT MARGIN
SELECT
    company_id,
    sales,
    net_profit,
    CASE
        WHEN sales > 0
        THEN ROUND((net_profit / sales) * 100, 2)
        ELSE NULL
    END AS net_profit_margin
FROM profitandloss
WHERE year = 2024
ORDER BY net_profit_margin DESC;


-- Q12. 2024 BALANCE SHEET CHECK
SELECT
    company_id,
    year,
    total_assets,
    total_liabilities,
    ROUND(
        total_assets - total_liabilities,
        2
    ) AS difference
FROM balancesheet
WHERE year = 2024
ORDER BY ABS(
    total_assets - total_liabilities
) DESC;


-- Q13. 2024 FINANCIAL RATIOS
SELECT
    company_id,
    pe_ratio,
    pb_ratio,
    roce,
    roe,
    debt_to_equity,
    current_ratio
FROM financial_ratios
WHERE year = 2024
ORDER BY roce DESC;


-- Q14. COMPANIES WITHOUT 2024 P&L
SELECT
    c.id,
    c.company_name
FROM companies c
LEFT JOIN profitandloss p
    ON c.id = p.company_id
    AND p.year = 2024
WHERE p.company_id IS NULL
ORDER BY c.id;


-- Q15. COMPANY + SECTOR SAMPLE
SELECT
    c.id,
    c.company_name,
    s.sector,
    s.industry
FROM companies c
LEFT JOIN sectors s
    ON c.id = s.company_id
ORDER BY c.id
LIMIT 20;