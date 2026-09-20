import sqlite3
from pathlib import Path
from typing import ClassVar

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class RadarChartGenerator:
    """Generate radar charts for all companies in the NIFTY 100 dataset."""

    AXES: ClassVar = [
        ("ROE", "roe"),
        ("ROCE", "roce"),
        ("NPM", "npm"),
        ("D/E", "debt_to_equity"),
        ("FCF Score", "fcf"),
        ("PAT CAGR 5yr", "pat_cagr_5yr"),
        ("Revenue CAGR 5yr", "revenue_cagr_5yr"),
        ("Composite Score", "composite_score"),
    ]

    def __init__(self):
        """Initialize database and output paths."""
        self.project_root = Path(__file__).resolve().parents[2]
        self.db_path = self.project_root / "data" / "nifty100.db"
        self.output_dir = self.project_root / "reports" / "radar_charts"

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_data(self):
        """Load companies, peer percentiles, peer groups, and ratio data."""
        conn = sqlite3.connect(self.db_path)

        peer_percentiles = pd.read_sql_query(
            """
            SELECT
                company_id,
                peer_group,
                metric,
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

        peer_groups = pd.read_sql_query(
            """
            SELECT
                company_id,
                peer_group
            FROM peer_groups
            WHERE peer_group IS NOT NULL
              AND TRIM(peer_group) <> ''
            """,
            conn,
        )

        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                composite_quality_score
            FROM financial_ratios
            """,
            conn,
        )

        conn.close()

        return peer_percentiles, companies, peer_groups, ratios

    @staticmethod
    def latest_composite(ratios):
        """Return the latest composite ratio record for each company."""
        ratios = ratios.copy()

        ratios["year"] = pd.to_numeric(ratios["year"], errors="coerce")

        return ratios.sort_values(["company_id", "year"]).drop_duplicates(
            "company_id",
            keep="last",
        )

    def build_chart_data(self):
        """Build radar-chart data for all companies."""
        peer_percentiles, companies, peer_groups, _ratios = self.load_data()

        from src.screener.composite_score import CompositeScorer

        scorer = CompositeScorer()
        sprint3_scores = scorer.calculate()

        sprint3_scores = sprint3_scores[
            ["company_id", "sprint3_composite_score"]
        ]

        percentile_metrics = [
            "roe",
            "roce",
            "npm",
            "debt_to_equity",
            "fcf",
            "pat_cagr_5yr",
            "revenue_cagr_5yr",
        ]

        if peer_percentiles.empty:
            pivot = companies.copy()
        else:
            pivot = peer_percentiles.pivot_table(
                index=["company_id", "peer_group"],
                columns="metric",
                values="percentile_rank",
                aggfunc="first",
            ).reset_index()

            pivot = pivot.merge(
                companies,
                on="company_id",
                how="right",
            )

        pivot = pivot.merge(
            peer_groups.drop_duplicates("company_id"),
            on="company_id",
            how="left",
            suffixes=("", "_group"),
        )

        if "peer_group" not in pivot.columns:
            pivot["peer_group"] = pivot["peer_group_group"]

        pivot["peer_group"] = pivot["peer_group"].fillna(
            pivot.get("peer_group_group", pd.Series(dtype="object"))
        )

        if "peer_group_group" in pivot.columns:
            pivot = pivot.drop(columns=["peer_group_group"])

        pivot = pivot.merge(
            sprint3_scores,
            on="company_id",
            how="left",
        )

        for metric in percentile_metrics:
            if metric in pivot.columns:
                pivot[metric] = pivot[metric] * 100

        pivot["composite_score"] = pivot["sprint3_composite_score"]

        if "peer_group" not in pivot.columns:
            pivot["peer_group"] = "No Peer Group"

        pivot["peer_group"] = pivot["peer_group"].fillna("No Peer Group")

        return pivot

    @staticmethod
    def peer_average(group_df, company_id):
        """Calculate the peer average for a company."""
        peers = group_df[group_df["company_id"] != company_id]

        if peers.empty:
            peers = group_df

        return peers

    @staticmethod
    def overall_average(data, company_id):
        """Calculate an overall fallback average for companies without peers."""
        peers = data[data["company_id"] != company_id]

        if peers.empty:
            peers = data

        return peers

    def create_radar(self, company_row, peer_rows, filename):
        """Create and save one radar chart."""
        labels = [label for label, _ in self.AXES]

        values = []

        for _, metric in self.AXES:
            value = company_row.get(metric, np.nan)

            if pd.isna(value):
                value = 50.0

            values.append(float(value))

        peer_values = []

        for _, metric in self.AXES:
            if metric not in peer_rows.columns:
                peer_values.append(50.0)
                continue

            peer_metric = pd.to_numeric(
                peer_rows[metric],
                errors="coerce",
            ).dropna()

            if peer_metric.empty:
                peer_values.append(50.0)
            else:
                peer_values.append(float(peer_metric.mean()))

        angles = np.linspace(
            0,
            2 * np.pi,
            len(labels),
            endpoint=False,
        )

        values_closed = values + [values[0]]
        peer_closed = peer_values + [peer_values[0]]
        angles_closed = np.concatenate(
            [angles, [angles[0]]]
        )

        fig = plt.figure(figsize=(8, 8))

        ax = fig.add_subplot(111, polar=True)

        ax.plot(
            angles_closed,
            values_closed,
            linewidth=2,
            label=str(company_row["company_id"]),
        )

        ax.fill(
            angles_closed,
            values_closed,
            alpha=0.15,
        )

        ax.plot(
            angles_closed,
            peer_closed,
            linestyle="--",
            linewidth=2,
            label="Peer Average",
        )

        ax.set_xticks(angles)
        ax.set_xticklabels(labels, fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])

        company_name = company_row.get(
            "company_name",
            company_row["company_id"],
        )

        peer_group = company_row.get(
            "peer_group",
            "No Peer Group",
        )

        ax.set_title(
            f"{company_name} ({company_row['company_id']})\n"
            f"{peer_group} - Peer Radar",
            pad=25,
            fontsize=13,
            fontweight="bold",
        )

        ax.legend(
            loc="upper right",
            bbox_to_anchor=(1.25, 1.10),
        )

        fig.tight_layout()

        fig.savefig(
            filename,
            dpi=160,
            bbox_inches="tight",
        )

        plt.close(fig)

    def generate(self):
        """Generate one radar chart for every company."""
        data = self.build_chart_data()

        generated = 0

        grouped = {
            group_name: group_df
            for group_name, group_df in data.groupby(
                "peer_group",
                dropna=False,
            )
        }

        overall_data = data.copy()

        for _, company_row in data.iterrows():
            company_id = company_row["company_id"]
            peer_group = company_row.get(
                "peer_group",
                "No Peer Group",
            )

            if peer_group == "No Peer Group":
                peer_rows = self.overall_average(
                    overall_data,
                    company_id,
                )
            else:
                peer_rows = grouped.get(
                    peer_group,
                    overall_data,
                )

                peer_rows = self.peer_average(
                    peer_rows,
                    company_id,
                )

            filename = (
                self.output_dir
                / f"{company_id}_radar.png"
            )

            self.create_radar(
                company_row,
                peer_rows,
                filename,
            )

            generated += 1

        return generated

    def print_summary(self, generated):
        """Print radar-chart generation summary."""
        files = list(
            self.output_dir.glob("*_radar.png")
        )

        print("=" * 70)
        print("SPRINT 3 RADAR CHART GENERATOR")
        print("=" * 70)
        print(f"Charts generated: {generated}")
        print(f"PNG files found: {len(files)}")
        print(f"Output directory: {self.output_dir}")
        print("=" * 70)


if __name__ == "__main__":
    generator = RadarChartGenerator()

    generated = generator.generate()

    generator.print_summary(generated)
