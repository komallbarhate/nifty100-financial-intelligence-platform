# Sprint 3 Retrospective — Screener + Peer Engine

## Sprint
Days 15–21

## Goal
Build and validate the Nifty 100 screener and peer-comparison engine.

## Completed

### Screener Engine
- Implemented a configurable screener engine.
- Added 6 screener presets:
  - Quality Compounder
  - Value Pick
  - Growth Accelerator
  - Dividend Champion
  - Debt-Free Blue Chip
  - Turnaround Watch
- Added 15 filterable metrics.
- Added Financials-specific debt-to-equity handling.
- Added debt-free interest coverage handling.
- Generated `output/screener_output.xlsx`.

### Composite Quality Score
- Implemented a 0–100 composite quality score.
- Profitability: 35%
- Cash Quality: 30%
- Growth: 20%
- Leverage: 15%
- Applied P10/P90 winsorisation.
- Applied sector-relative normalization.
- Scored all 92 companies.

### Peer Engine
- Loaded 11 peer groups.
- Calculated percentile rankings across 10 metrics.
- Generated 560 percentile records for 56 peer-assigned companies.
- Applied inverse percentile ranking for debt-to-equity.

### Radar Charts
- Generated 56 radar charts.
- Each chart contains company metrics and peer-average comparison.

### Peer Comparison Workbook
- Generated `output/peer_comparison.xlsx`.
- Created 11 peer-group sheets.
- Included company metrics, percentile rankings, benchmark indicators and peer median.

## Final Validation

### Sprint 3 Verification
- 16/16 checks passed.
- 14/14 data-quality checks passed.
- Quality Compounder acceptance check passed.
- IT Services ROE percentile acceptance check passed.

### Automated Tests
- 54/54 pytest tests passed.
- HTML test report generated at `reports/pytest_report.html`.

### Database
- SQLite integrity check: OK.
- Foreign-key failures: 0.
- `peer_percentiles`: 560 rows.
- Peer companies: 56.
- Peer groups: 11.
- Peer metrics: 10.

## Key Outputs

- `output/screener_output.xlsx`
- `output/peer_comparison.xlsx`
- `reports/radar_charts/`
- `reports/pytest_report.html`
- `reports/sprint1_retrospective.md`
- `reports/sprint2_retrospective.md`
- `reports/sprint3_retrospective.md`
- `config/screener_config.yaml`
- `src/screener/`
- `src/analytics/peer.py`
- `src/analytics/peer_workbook.py`
- `src/analytics/radar.py`

## What Went Well

- Screener configuration was separated from engine logic.
- Peer percentile calculations were validated against expected group and metric counts.
- Database integrity was explicitly checked before sprint closure.
- Existing KPI tests remained fully passing.

## Debugging Completed

- Market-cap source schema was rebuilt to match the required database structure.
- Peer-group source data was loaded into the database.
- The market-cap foreign key was corrected to reference `companies(id)`.
- The final verifier was corrected so the project root is available when the script is executed directly from `src`.

## Sprint Outcome

Sprint 3 acceptance criteria were satisfied with 16/16 verification checks and 54/54 automated tests passing.
