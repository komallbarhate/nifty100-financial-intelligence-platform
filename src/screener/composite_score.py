import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"


class CompositeScorer:

    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        self.data = self._load_data()

    def _load_data(self):

        conn = sqlite3.connect(self.db_path)

        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                return_on_equity_pct,
                return_on_capital_employed_pct,
                net_profit_margin_pct,
                debt_to_equity,
                interest_coverage,
                free_cash_flow_cr,
                cash_from_operations_cr,
                cfo_pat_ratio,
                revenue_cagr_5yr,
                pat_cagr_5yr
            FROM financial_ratios
            """,
            conn,
        )

        sectors = pd.read_sql_query(
            """
            SELECT
                company_id,
                sector,
                industry
            FROM sectors
            """,
            conn,
        )

        conn.close()

        ratios["company_id"] = ratios["company_id"].astype(str).str.strip().str.upper()

        sectors["company_id"] = (
            sectors["company_id"].astype(str).str.strip().str.upper()
        )

        numeric_columns = [
            "return_on_equity_pct",
            "return_on_capital_employed_pct",
            "net_profit_margin_pct",
            "debt_to_equity",
            "interest_coverage",
            "free_cash_flow_cr",
            "cash_from_operations_cr",
            "cfo_pat_ratio",
            "revenue_cagr_5yr",
            "pat_cagr_5yr",
        ]

        for column in numeric_columns:
            ratios[column] = pd.to_numeric(
                ratios[column],
                errors="coerce",
            )

        ratios["year"] = pd.to_numeric(
            ratios["year"],
            errors="coerce",
        )

        df = ratios.merge(
            sectors,
            on="company_id",
            how="left",
        )

        df = df.sort_values(["company_id", "year"])

        return df.reset_index(drop=True)

    def calculate_fcf_cagr(self):
        """Calculate fcf cagr."""
        result = {}

        for company_id, group in self.data.groupby("company_id"):

            group = group.dropna(subset=["year"]).sort_values("year")

            latest_year = int(group["year"].max())

            target_year = latest_year - 5

            base_rows = group[group["year"] == target_year]

            latest_rows = group[group["year"] == latest_year]

            if base_rows.empty or latest_rows.empty:
                result[company_id] = np.nan
                continue

            base = base_rows.iloc[-1]["free_cash_flow_cr"]

            latest = latest_rows.iloc[-1]["free_cash_flow_cr"]

            if pd.isna(base) or pd.isna(latest):
                result[company_id] = np.nan

            elif base > 0 and latest > 0:
                result[company_id] = ((latest / base) ** (1 / 5) - 1) * 100

            elif base == 0 or base < 0 and latest < 0:
                result[company_id] = np.nan

            else:
                result[company_id] = np.nan

        return pd.Series(result, name="fcf_cagr_5yr")

    @staticmethod
    def _winsorize_and_normalize(
        series,
        higher_is_better=True,
    ):

        values = pd.to_numeric(
            series,
            errors="coerce",
        )

        valid = values.dropna()

        if len(valid) == 0:
            return pd.Series(
                50.0,
                index=series.index,
            )

        p10 = valid.quantile(0.10)
        p90 = valid.quantile(0.90)

        if p10 == p90:
            return pd.Series(
                50.0,
                index=series.index,
            )

        clipped = values.clip(
            lower=p10,
            upper=p90,
        )

        if higher_is_better:

            score = ((clipped - p10) / (p90 - p10)) * 100

        else:

            score = ((p90 - clipped) / (p90 - p10)) * 100

        return score.fillna(50.0)

    def _sector_relative_score(
        self,
        df,
        column,
        higher_is_better=True,
    ):

        result = pd.Series(
            np.nan,
            index=df.index,
        )

        for sector, indexes in df.groupby(
            "sector",
            dropna=False,
        ).groups.items():

            values = df.loc[
                indexes,
                column,
            ]

            result.loc[indexes] = self._winsorize_and_normalize(
                values,
                higher_is_better,
            )

        return result

    def calculate(self):
        """Process calculate."""
        df = (
            self.data.sort_values(["company_id", "year"])
            .groupby(
                "company_id",
                as_index=False,
            )
            .tail(1)
            .copy()
        )

        fcf_cagr = self.calculate_fcf_cagr()

        df["fcf_cagr_5yr"] = df["company_id"].map(fcf_cagr)

        df["fcf_positive"] = df["free_cash_flow_cr"] > 0

        # ---------------------------------------------------------
        # Sector-relative normalized metrics
        # ---------------------------------------------------------

        df["roe_score"] = self._sector_relative_score(
            df,
            "return_on_equity_pct",
            True,
        )

        df["roce_score"] = self._sector_relative_score(
            df,
            "return_on_capital_employed_pct",
            True,
        )

        df["npm_score"] = self._sector_relative_score(
            df,
            "net_profit_margin_pct",
            True,
        )

        df["fcf_cagr_score"] = self._sector_relative_score(
            df,
            "fcf_cagr_5yr",
            True,
        )

        df["cfo_pat_score"] = self._sector_relative_score(
            df,
            "cfo_pat_ratio",
            True,
        )

        df["revenue_growth_score"] = self._sector_relative_score(
            df,
            "revenue_cagr_5yr",
            True,
        )

        df["pat_growth_score"] = self._sector_relative_score(
            df,
            "pat_cagr_5yr",
            True,
        )

        df["debt_to_equity_score"] = self._sector_relative_score(
            df,
            "debt_to_equity",
            False,
        )

        df["icr_score"] = self._sector_relative_score(
            df,
            "interest_coverage",
            True,
        )

        # ---------------------------------------------------------
        # Cash quality positive-FCF component
        # ---------------------------------------------------------

        df["fcf_positive_score"] = df["fcf_positive"].astype(float) * 100

        # ---------------------------------------------------------
        # Component scores
        # ---------------------------------------------------------

        df["profitability_score"] = (
            df["roe_score"] * 0.15 + df["roce_score"] * 0.10 + df["npm_score"] * 0.10
        )

        df["cash_quality_score"] = (
            df["fcf_cagr_score"] * 0.15
            + df["cfo_pat_score"] * 0.10
            + df["fcf_positive_score"] * 0.05
        )

        df["growth_score"] = (
            df["revenue_growth_score"] * 0.10 + df["pat_growth_score"] * 0.10
        )

        df["leverage_score"] = (
            df["debt_to_equity_score"] * 0.10 + df["icr_score"] * 0.05
        )

        df["sprint3_composite_score"] = (
            df["profitability_score"]
            + df["cash_quality_score"]
            + df["growth_score"]
            + df["leverage_score"]
        )

        df["sprint3_composite_score"] = df["sprint3_composite_score"].clip(0, 100)

        return df.sort_values(
            "sprint3_composite_score",
            ascending=False,
        ).reset_index(drop=True)


def main():
    """Run the main workflow."""
    scorer = CompositeScorer()

    result = scorer.calculate()

    print("=" * 70)
    print("SPRINT 3 COMPOSITE SCORE")
    print("=" * 70)

    print(f"Companies scored: " f"{result['company_id'].nunique()}")

    print(f"Score minimum: " f"{result['sprint3_composite_score'].min():.2f}")

    print(f"Score maximum: " f"{result['sprint3_composite_score'].max():.2f}")

    print(f"Score average: " f"{result['sprint3_composite_score'].mean():.2f}")

    print()
    print("Top 10 by Sprint 3 composite score:")

    columns = [
        "company_id",
        "sector",
        "profitability_score",
        "cash_quality_score",
        "growth_score",
        "leverage_score",
        "sprint3_composite_score",
    ]

    print(result[columns].head(10).to_string(index=False))

    print()
    print(
        "FCF CAGR available:",
        result["fcf_cagr_5yr"].notna().sum(),
        "/",
        len(result),
    )


if __name__ == "__main__":
    main()
