# Sprint 2 Retrospective — Financial Ratio Engine

## Sprint Status

**SPRINT 2: COMPLETE**

## Duration

Days 08–14

## Objective

Build a financial ratio engine covering the available annual financial history of the 92-company NIFTY 100 dataset.

## Final Database Coverage

- Companies: **92**
- Financial ratio rows: **1073**
- Companies represented in ratio table: **92**
- Foreign-key errors: **0**
- SQLite integrity: **ok**

## KPI Engine

Implemented profitability, leverage, efficiency, cash-flow, growth and composite-quality calculations.

Core KPI groups:

- Net Profit Margin
- Operating Profit Margin
- Return on Equity
- Return on Capital Employed
- Return on Assets
- Debt to Equity
- Interest Coverage
- Net Debt
- Asset Turnover
- Free Cash Flow
- CapEx
- EPS
- Book Value per Share
- Dividend Payout
- CFO
- CFO/PAT
- CapEx Intensity
- FCF Conversion
- Revenue CAGR
- PAT CAGR
- EPS CAGR
- Composite Quality Score

## CAGR Edge Cases

The engine handles:

- Valid positive-to-positive CAGR
- Decline to loss
- Turnaround
- Both negative
- Zero base
- Insufficient history

## Financials Carve-Out

Financials were identified using the supplied sector classification rather than ticker-name heuristics.

Financials companies identified: **23**

Financial high-leverage warnings after carve-out: **0**

## Day 13 Source Comparisons

ROE and ROCE calculated values were compared with source company-level values.

Differences above the 5 percentage-point threshold were logged as edge cases rather than silently replacing calculated values.

## Testing

KPI test suite result:

**54 tests passed**

## Screener

Created four analytical screens:

1. Profitability
2. Growth
3. Balance Sheet
4. Cash Flow

A five-company demonstration dataset was also created.

## Output Artifacts

- output/day13_financials_edge_cases.csv
- output/day13_report.md
- output/screener_profitability.csv
- output/screener_growth.csv
- output/screener_balance_sheet.csv
- output/screener_cashflow.csv
- output/day14_five_company_demo.csv

## Important Data Limitation

The annual P&L source provides **1,073 valid company-year observations across 92 companies**. The ratio engine therefore generates 1,073 annual ratio rows rather than fabricating records to reach an arbitrary 1,100-row threshold.

## Lessons Learned

1. Source column mappings must be validated before database loading.
2. Reporting periods can create duplicate-year records and require deterministic handling.
3. Financial ratio calculations need explicit handling for zero and negative denominators.
4. CAGR requires sufficient historical observations.
5. Sector classifications should come from the supplied sector dataset rather than ticker-name heuristics.
6. Source KPI values should be compared with calculated values and logged when materially different.
7. Missing financial data should not be silently interpreted as economic zero.

## Sprint 2 Exit Criteria

- 92-company coverage: **PASS**
- Financial ratio engine: **PASS**
- CAGR edge cases: **PASS**
- Financials carve-out: **PASS**
- KPI tests: **PASS**
- Screener: **PASS**
- Five-company demo: **PASS**
- Database integrity: **PASS**
- Required output artifacts: **PASS**

# FINAL RESULT

**SPRINT 2 SUCCESSFULLY COMPLETED**
