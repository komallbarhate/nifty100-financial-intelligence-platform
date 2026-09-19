from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


class PeerEngine:

    METRICS = {
        "roe": {
            "column": "return_on_equity_pct",
            "higher_is_better": True,
        },
        "roce": {
            "column": "return_on_capital_employed_pct",
            "higher_is_better": True,
        },
        "npm": {
            "column": "net_profit_margin_pct",
            "higher_is_better": True,
        },
        "debt_to_equity": {
            "column": "debt_to_equity",
            "higher_is_better": False,
        },
        "fcf": {
            "column": "free_cash_flow_cr",
            "higher_is_better": True,
        },
        "pat_cagr_5yr": {
            "column": "pat_cagr_5yr",
            "higher_is_better": True,
        },
        "revenue_cagr_5yr": {
            "column": "revenue_cagr_5yr",
            "higher_is_better": True,
        },
        "eps_cagr_5yr": {
            "column": "eps_cagr_5yr",
            "higher_is_better": True,
        },
        "icr": {
            "column": "interest_coverage",
            "higher_is_better": True,
        },
        "asset_turnover": {
            "column": "asset_turnover",
            "higher_is_better": True,
        },
    }

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.db_path = self.project_root / "data" / "nifty100.db"

    def load_data(self):
        conn = sqlite3.connect(self.db_path)

        ratios = pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            """,
            conn
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
            conn
        )

        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            """,
            conn
        )

        conn.close()

        return ratios, peer_groups, companies

    @staticmethod
    def latest_rows(df):
        df = df.copy()

        df["year"] = pd.to_numeric(
            df["year"],
            errors="coerce"
        )

        return (
            df.sort_values(
                ["company_id", "year"]
            )
            .drop_duplicates(
                "company_id",
                keep="last"
            )
        )

    @staticmethod
    def percentile_rank(series):
        """
        SQL-style PERCENT_RANK:

            (rank - 1) / (n - 1)

        Ties receive the average rank.
        A single-company group receives 1.0.
        """
        series = pd.to_numeric(
            series,
            errors="coerce"
        )

        valid = series.notna()

        result = pd.Series(
            np.nan,
            index=series.index,
            dtype=float
        )

        values = series[valid]

        if len(values) == 0:
            return result

        if len(values) == 1:
            result.loc[values.index] = 1.0
            return result

        ranks = values.rank(
            method="average",
            ascending=True
        )

        result.loc[values.index] = (
            (ranks - 1) / (len(values) - 1)
        )

        return result

    def build_percentiles(self):
        ratios, peer_groups, companies = self.load_data()

        ratios_latest = self.latest_rows(ratios)

        # Debt-free companies get infinite ICR.
        debt_free = (
            ratios_latest["debt_to_equity"]
            .fillna(np.nan)
            .eq(0)
            & ratios_latest["interest_coverage"].isna()
        )

        ratios_latest.loc[
            debt_free,
            "interest_coverage"
        ] = np.inf

        df = ratios_latest.merge(
            peer_groups,
            on="company_id",
            how="left"
        )

        df = df.merge(
            companies,
            on="company_id",
            how="left"
        )

        rows = []

        for metric_name, config in self.METRICS.items():

            column = config["column"]

            if column not in df.columns:
                continue

            metric_df = df[
                [
                    "company_id",
                    "company_name",
                    "year",
                    "peer_group",
                    column,
                ]
            ].copy()

            metric_df["value"] = pd.to_numeric(
                metric_df[column],
                errors="coerce"
            )

            metric_df = metric_df.drop(
                columns=[column]
            )

            # Companies without a peer group are retained
            # separately so they can be reported, but they
            # do not receive a peer percentile.
            grouped = metric_df[
                metric_df["peer_group"].notna()
            ].copy()

            if grouped.empty:
                continue

            grouped["percentile_rank"] = (
                grouped
                .groupby("peer_group")["value"]
                .transform(self.percentile_rank)
            )

            # Debt-to-equity is inverse:
            # lower D/E = better percentile.
            if not config["higher_is_better"]:
                grouped["percentile_rank"] = (
                    1.0 - grouped["percentile_rank"]
                )

            grouped["metric"] = metric_name

            rows.append(
                grouped[
                    [
                        "company_id",
                        "peer_group",
                        "metric",
                        "value",
                        "percentile_rank",
                        "year",
                    ]
                ]
            )

        if not rows:
            return pd.DataFrame(
                columns=[
                    "company_id",
                    "peer_group",
                    "metric",
                    "value",
                    "percentile_rank",
                    "year",
                ]
            )

        result = pd.concat(
            rows,
            ignore_index=True
        )

        result["percentile_rank"] = (
            result["percentile_rank"]
            .clip(0, 1)
        )

        return result

    def save_to_database(self, result):
        conn = sqlite3.connect(self.db_path)

        conn.execute(
            """
            DROP TABLE IF EXISTS peer_percentiles
            """
        )

        conn.execute(
            """
            CREATE TABLE peer_percentiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id TEXT NOT NULL,
                peer_group TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL,
                percentile_rank REAL,
                year INTEGER,
                UNIQUE(
                    company_id,
                    peer_group,
                    metric,
                    year
                )
            )
            """
        )

        result.to_sql(
            "peer_percentiles",
            conn,
            if_exists="append",
            index=False
        )

        conn.commit()
        conn.close()

    def run(self):
        result = self.build_percentiles()

        self.save_to_database(result)

        return result

    def print_summary(self, result):
        print("=" * 70)
        print("SPRINT 3 PEER PERCENTILE ENGINE")
        print("=" * 70)

        print(
            f"Rows generated: {len(result)}"
        )

        print(
            f"Companies with peer groups: "
            f"{result['company_id'].nunique()}"
        )

        print(
            f"Peer groups: "
            f"{result['peer_group'].nunique()}"
        )

        print(
            f"Metrics: "
            f"{result['metric'].nunique()}"
        )

        print()

        print("Peer groups:")
        for group, count in (
            result.groupby("peer_group")["company_id"]
            .nunique()
            .sort_index()
            .items()
        ):
            print(
                f"  {group}: {count} companies"
            )

        print()

        print("Metrics:")
        for metric, count in (
            result.groupby("metric")["company_id"]
            .nunique()
            .sort_index()
            .items()
        ):
            print(
                f"  {metric}: {count} companies"
            )

        print()

        print(
            "Percentile range:",
            result["percentile_rank"].min(),
            "to",
            result["percentile_rank"].max()
        )

        print()
        print("Database table: peer_percentiles")
        print("=" * 70)


if __name__ == "__main__":
    engine = PeerEngine()

    result = engine.run()

    engine.print_summary(result)
