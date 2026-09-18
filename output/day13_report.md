# Sprint 2 Day 13 — Financials & Edge-Case Audit

## Status

DAY 13 IMPLEMENTATION: COMPLETE

## Sector Coverage

- Companies in sectors table: **92**
- Companies with populated broad sector: **92**

### Sector distribution

| Sector | Companies |
|---|---:|
| Financials | 23 |
| Energy | 14 |
| Consumer Discretionary | 14 |
| Industrials | 10 |
| Materials | 9 |
| Consumer Staples | 7 |
| Healthcare | 6 |
| Information Technology | 5 |
| Real Estate | 2 |
| Communication Services | 2 |

## Financials Carve-Out

- Financials companies identified from source: **23**
- Ratio rows belonging to Financials: **258**
- Financials high-leverage warnings remaining: **0**
- Non-Financial high-leverage warnings: **18**

### Financial company IDs

AXISBANK, BAJAJFINSV, BAJAJHLDNG, BAJFINANCE, BANKBARODA, CANBK, CHOLAFIN, HDFCBANK, HDFCLIFE, ICICIBANK, ICICIGI, ICICIPRULI, INDUSINDBK, IRFC, JIOFIN, KOTAKBANK, LICI, PFC, PNB, RECLTD, SBILIFE, SBIN, SHRIRAMFIN

## ROE Source Comparison

- ROE differences >5 percentage points: **529**
- These are logged as source/calculation comparison edge cases; the calculated KPI is not silently overwritten.

## ROCE Source Comparison

- ROCE differences >5 percentage points: **576**
- These are logged as source/calculation comparison edge cases.

## Edge-Case Categories

- ROE_SOURCE_ANOMALY: calculated ROE differs from source ROE by >5 percentage points.
- ROCE_SOURCE_ANOMALY: calculated ROCE differs from source ROCE by >5 percentage points.
- ROE_AND_ROCE_DIFFERENCE: both comparisons exceed the 5-point threshold.
- Financials D/E carve-out: high-leverage warning suppressed for Financials.

## Output Files

- output/day13_financials_edge_cases.csv
- output/day13_report.md

## Day 13 Validation

- Sector rows = 92: PASS
- Sector values populated = 92: PASS
- Financials D/E warnings = 0: PASS
- ROE/ROCE anomalies logged rather than silently altered: PASS

### Final result

**DAY 13 COMPLETE**