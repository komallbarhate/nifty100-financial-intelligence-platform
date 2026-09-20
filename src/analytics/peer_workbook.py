import sqlite3
from pathlib import Path
from typing import ClassVar

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


class PeerComparisonWorkbook:

    METRICS: ClassVar = [
        "roe",
        "roce",
        "npm",
        "debt_to_equity",
        "fcf",
        "pat_cagr_5yr",
        "revenue_cagr_5yr",
        "eps_cagr_5yr",
        "icr",
        "asset_turnover",
    ]

    METRIC_LABELS: ClassVar = {
        "roe": "ROE",
        "roce": "ROCE",
        "npm": "NPM",
        "debt_to_equity": "D/E",
        "fcf": "FCF",
        "pat_cagr_5yr": "PAT CAGR 5yr",
        "revenue_cagr_5yr": "Revenue CAGR 5yr",
        "eps_cagr_5yr": "EPS CAGR 5yr",
        "icr": "ICR",
        "asset_turnover": "Asset Turnover",
    }

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.db_path = self.project_root / "data" / "nifty100.db"
        self.source_path = (
            self.project_root
            / "data"
            / "supporting"
            / "1788501620796-5060f580-peer_groups.xlsx"
        )
        self.output_path = self.project_root / "output" / "peer_comparison.xlsx"

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def load_data(self):
        """Load data."""
        conn = sqlite3.connect(self.db_path)

        percentiles = pd.read_sql_query(
            """
            SELECT
                company_id,
                peer_group,
                metric,
                value,
                percentile_rank,
                year
            FROM peer_percentiles
            """,
            conn,
        )

        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            """,
            conn,
        )

        conn.close()

        benchmark_source = pd.read_excel(self.source_path)

        benchmark_source["company_id"] = (
            benchmark_source["company_id"]
            .astype(str)
            .str.strip()
            .str.upper()
            .replace({"BAJAJ-AUTO": "BAJAJAUTO"})
        )

        benchmark_source["is_benchmark"] = (
            benchmark_source["is_benchmark"]
            .astype(str)
            .str.strip()
            .str.lower()
            .eq("true")
        )

        benchmarks = benchmark_source[
            ["company_id", "peer_group_name", "is_benchmark"]
        ].copy()

        return (percentiles, companies, benchmarks)

    def build_data(self):
        """Build data."""
        percentiles, companies, benchmarks = self.load_data()

        percentiles = percentiles.merge(companies, on="company_id", how="left")

        # Convert percentile to 0-100 for workbook display.
        percentiles["percentile_100"] = percentiles["percentile_rank"] * 100

        value_pivot = percentiles.pivot_table(
            index=[
                "company_id",
                "peer_group",
                "company_name",
                "year",
            ],
            columns="metric",
            values="value",
            aggfunc="first",
        ).reset_index()

        percentile_pivot = percentiles.pivot_table(
            index=[
                "company_id",
                "peer_group",
                "company_name",
                "year",
            ],
            columns="metric",
            values="percentile_100",
            aggfunc="first",
        ).reset_index()

        value_pivot = value_pivot.rename(
            columns={
                metric: f"{self.METRIC_LABELS[metric]}"
                for metric in self.METRICS
                if metric in value_pivot.columns
            }
        )

        percentile_pivot = percentile_pivot.rename(
            columns={
                metric: f"{self.METRIC_LABELS[metric]} Percentile"
                for metric in self.METRICS
                if metric in percentile_pivot.columns
            }
        )

        key_columns = [
            "company_id",
            "peer_group",
            "company_name",
            "year",
        ]

        result = value_pivot[key_columns].copy()

        for metric in self.METRICS:
            label = self.METRIC_LABELS[metric]

            if label in value_pivot.columns:
                result[label] = value_pivot[label]

            percentile_label = f"{label} Percentile"

            if percentile_label in percentile_pivot.columns:
                result[percentile_label] = percentile_pivot[percentile_label]

        result = result.merge(
            benchmarks[["company_id", "is_benchmark"]], on="company_id", how="left"
        )

        result["is_benchmark"] = result["is_benchmark"].fillna(False).astype(bool)

        return result

    def create_workbook(self):
        """Create workbook."""
        data = self.build_data()

        peer_groups = sorted(data["peer_group"].dropna().unique().tolist())

        with pd.ExcelWriter(self.output_path, engine="openpyxl") as writer:

            for peer_group in peer_groups:

                group = data[data["peer_group"] == peer_group].copy()

                group = group.sort_values(
                    ["is_benchmark", "company_name"], ascending=[False, True]
                )

                # Put benchmark indicator first.
                group["Benchmark"] = group["is_benchmark"].map({True: "YES", False: ""})

                columns = [
                    "company_id",
                    "company_name",
                    "Benchmark",
                ]

                for metric in self.METRICS:
                    label = self.METRIC_LABELS[metric]

                    columns.append(label)
                    columns.append(f"{label} Percentile")

                columns.append("year")

                group = group[columns]

                sheet_name = peer_group[:31]

                group.to_excel(writer, sheet_name=sheet_name, index=False)

        self.format_workbook(peer_groups)

        return peer_groups

    def format_workbook(self, peer_groups):
        """Format workbook."""
        wb = load_workbook(self.output_path)

        header_fill = PatternFill(fill_type="solid", fgColor="1F4E78")

        header_font = Font(color="FFFFFF", bold=True)

        green_fill = PatternFill(fill_type="solid", fgColor="C6EFCE")

        yellow_fill = PatternFill(fill_type="solid", fgColor="FFEB9C")

        red_fill = PatternFill(fill_type="solid", fgColor="FFC7CE")

        benchmark_fill = PatternFill(fill_type="solid", fgColor="FFD966")

        for peer_group in peer_groups:

            ws = wb[peer_group[:31]]

            headers = {cell.value: cell.column for cell in ws[1]}

            # Header formatting.
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # Benchmark rows.
            benchmark_col = headers.get("Benchmark")

            if benchmark_col:

                for row in range(2, ws.max_row + 1):

                    value = ws.cell(row=row, column=benchmark_col).value

                    if value == "YES":

                        for col in range(1, ws.max_column + 1):
                            ws.cell(row=row, column=col).fill = benchmark_fill

            # Percentile coloring.
            for header, column in headers.items():

                if not str(header).endswith(" Percentile"):
                    continue

                for row in range(2, ws.max_row + 1):

                    cell = ws.cell(row=row, column=column)

                    if not isinstance(cell.value, (int, float)):
                        continue

                    value = float(cell.value)

                    if value >= 75:
                        cell.fill = green_fill

                    elif value <= 25:
                        cell.fill = red_fill

                    else:
                        cell.fill = yellow_fill

                    cell.number_format = "0.00"

            # Number formatting.
            for header, column in headers.items():

                if header in [
                    "ROE",
                    "ROCE",
                    "NPM",
                    "PAT CAGR 5yr",
                    "Revenue CAGR 5yr",
                    "EPS CAGR 5yr",
                ] or header in [
                    "D/E",
                    "ICR",
                    "Asset Turnover",
                ]:
                    for row in range(2, ws.max_row + 1):
                        ws.cell(row=row, column=column).number_format = "0.00"

                elif header == "FCF":
                    for row in range(2, ws.max_row + 1):
                        ws.cell(row=row, column=column).number_format = "#,##0.00"

            # Peer median row.
            data_start = 2
            data_end = ws.max_row

            median_row = ws.max_row + 2

            ws.cell(row=median_row, column=1, value="PEER MEDIAN")

            ws.cell(row=median_row, column=1).font = Font(bold=True)

            for header, column in headers.items():

                if header in [
                    "ROE",
                    "ROCE",
                    "NPM",
                    "D/E",
                    "FCF",
                    "PAT CAGR 5yr",
                    "Revenue CAGR 5yr",
                    "EPS CAGR 5yr",
                    "ICR",
                    "Asset Turnover",
                ]:

                    values = []

                    for row in range(data_start, data_end + 1):
                        value = ws.cell(row=row, column=column).value

                        if isinstance(value, (int, float)):
                            values.append(float(value))

                    if values:
                        ws.cell(
                            row=median_row,
                            column=column,
                            value=float(pd.Series(values).median()),
                        )

                        ws.cell(row=median_row, column=column).number_format = "0.00"

            for col in range(1, ws.max_column + 1):
                ws.cell(row=median_row, column=col).fill = PatternFill(
                    fill_type="solid", fgColor="D9EAD3"
                )

                ws.cell(row=median_row, column=col).font = Font(bold=True)

            ws.freeze_panes = "A2"

            # Autofit.
            for column_cells in ws.columns:

                max_length = 0

                column_letter = get_column_letter(column_cells[0].column)

                for cell in column_cells:
                    if cell.value is not None:
                        max_length = max(max_length, len(str(cell.value)))

                ws.column_dimensions[column_letter].width = min(
                    max(max_length + 2, 12), 28
                )

        wb.save(self.output_path)

    def run(self):
        """Run the workflow."""
        peer_groups = self.create_workbook()

        print("=" * 70)
        print("SPRINT 3 PEER COMPARISON WORKBOOK")
        print("=" * 70)
        print(f"Created: {self.output_path}")
        print(f"Peer group sheets: {len(peer_groups)}")

        for group in peer_groups:
            print(f"  - {group}")

        print("=" * 70)


if __name__ == "__main__":
    PeerComparisonWorkbook().run()



