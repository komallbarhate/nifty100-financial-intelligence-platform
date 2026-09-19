from pathlib import Path
import sqlite3
import yaml
import numpy as np
import pandas as pd

from src.screener.composite_score import CompositeScorer


class ScreenerEngine:

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.db_path = self.project_root / "data" / "nifty100.db"
        self.config_path = self.project_root / "config" / "screener_config.yaml"

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.conn = sqlite3.connect(self.db_path)

    def load_data(self):
        ratios = pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            """,
            self.conn
        )

        pnl = pd.read_sql_query(
            """
            SELECT *
            FROM profitandloss
            """,
            self.conn
        )

        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            """,
            self.conn
        )

        sectors = pd.read_sql_query(
            """
            SELECT
                company_id,
                sector,
                industry
            FROM sectors
            """,
            self.conn
        )

        market_cap = pd.read_sql_query(
            """
            SELECT *
            FROM market_cap
            """,
            self.conn
        )

        return ratios, pnl, companies, sectors, market_cap

    @staticmethod
    def latest_rows(df, year_column="year"):
        if df.empty:
            return df.copy()

        df = df.copy()
        df[year_column] = pd.to_numeric(df[year_column], errors="coerce")

        return (
            df.sort_values(year_column)
            .drop_duplicates("company_id", keep="last")
        )

    def build_dataset(self):
        ratios, pnl, companies, sectors, market_cap = self.load_data()

        ratios_latest = self.latest_rows(ratios)

        pnl_latest = self.latest_rows(pnl)

        market_cap_latest = self.latest_rows(market_cap)

        df = companies.copy()

        df = df.merge(
            ratios_latest,
            on="company_id",
            how="left",
            suffixes=("", "_ratio")
        )

        df = df.merge(
            pnl_latest,
            on="company_id",
            how="left",
            suffixes=("", "_pnl")
        )

        df = df.merge(
            sectors,
            on="company_id",
            how="left"
        )

        df = df.merge(
            market_cap_latest[
                [
                    "company_id",
                    "year",
                    "market_cap_crore",
                    "enterprise_value_crore",
                    "pe_ratio",
                    "pb_ratio",
                    "ev_ebitda",
                    "dividend_yield_pct"
                ]
            ],
            on="company_id",
            how="left",
            suffixes=("", "_market")
        )

        # Prefer the latest financial-ratio year.
        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce")

        numeric_columns = [
            "return_on_equity_pct",
            "return_on_capital_employed_pct",
            "net_profit_margin_pct",
            "debt_to_equity",
            "interest_coverage",
            "asset_turnover",
            "free_cash_flow_cr",
            "cash_from_operations_cr",
            "cfo_pat_ratio",
            "revenue_cagr_3yr",
            "revenue_cagr_5yr",
            "revenue_cagr_10yr",
            "pat_cagr_3yr",
            "pat_cagr_5yr",
            "pat_cagr_10yr",
            "eps_cagr_3yr",
            "eps_cagr_5yr",
            "eps_cagr_10yr",
            "dividend_payout_ratio_pct",
            "earnings_per_share",
            "book_value_per_share",
            "total_debt_cr",
            "market_cap_crore",
            "enterprise_value_crore",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield_pct",
        ]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Latest sales and net profit from P&L.
        sales_candidates = [
            "sales",
            "revenue",
            "revenue_cr",
            "sales_cr"
        ]

        sales_col = next(
            (c for c in sales_candidates if c in df.columns),
            None
        )

        if sales_col:
            df["sales"] = pd.to_numeric(df[sales_col], errors="coerce")
        else:
            df["sales"] = np.nan

        profit_candidates = [
            "net_profit",
            "net_profit_cr",
            "profit_after_tax",
            "pat"
        ]

        profit_col = next(
            (c for c in profit_candidates if c in df.columns),
            None
        )

        if profit_col:
            df["net_profit"] = pd.to_numeric(
                df[profit_col],
                errors="coerce"
            )
        else:
            df["net_profit"] = np.nan

        # Debt-free companies get infinite ICR for screener purposes.
        debt_free_mask = (
            df["debt_to_equity"].fillna(np.nan).eq(0)
            & df["interest_coverage"].isna()
        )

        df.loc[debt_free_mask, "interest_coverage"] = np.inf

        # Calculate whether D/E is declining year-over-year.
        ratio_history = ratios.copy()

        ratio_history["year"] = pd.to_numeric(
            ratio_history["year"],
            errors="coerce"
        )

        ratio_history["debt_to_equity"] = pd.to_numeric(
            ratio_history["debt_to_equity"],
            errors="coerce"
        )

        ratio_history = ratio_history.sort_values(
            ["company_id", "year"]
        )

        ratio_history["previous_debt_to_equity"] = (
            ratio_history
            .groupby("company_id")["debt_to_equity"]
            .shift(1)
        )

        latest_ratio_history = self.latest_rows(ratio_history)

        latest_ratio_history["debt_to_equity_declining"] = (
            latest_ratio_history["debt_to_equity"]
            < latest_ratio_history["previous_debt_to_equity"]
        )

        df = df.drop(
            columns=["debt_to_equity_declining"],
            errors="ignore"
        )

        df = df.merge(
            latest_ratio_history[
                [
                    "company_id",
                    "debt_to_equity_declining"
                ]
            ],
            on="company_id",
            how="left"
        )

        # Sprint 3 composite score.
        scorer = CompositeScorer()
        scored = scorer.calculate()

        score_columns = [
            "company_id",
            "profitability_score",
            "cash_quality_score",
            "growth_score",
            "leverage_score",
            "sprint3_composite_score"
        ]

        df = df.drop(
            columns=[
                "profitability_score",
                "cash_quality_score",
                "growth_score",
                "leverage_score",
                "sprint3_composite_score"
            ],
            errors="ignore"
        )

        df = df.merge(
            scored[score_columns],
            on="company_id",
            how="left"
        )

        return df

    def apply_filter(self, df, metric, condition):
        if metric not in df.columns:
            return df

        result = df.copy()

        if "min" in condition:
            result = result[
                result[metric] >= condition["min"]
            ]

        if "max" in condition:
            result = result[
                result[metric] <= condition["max"]
            ]

        if "equals" in condition:
            result = result[
                result[metric] == condition["equals"]
            ]

        return result

    def apply_preset(self, df, preset_key):
        preset = self.config["presets"][preset_key]

        result = df.copy()

        financials_name = self.config["financials_sector"]["name"]

        for metric, condition in preset["filters"].items():

            if (
                metric == "debt_to_equity"
                and self.config["financials_sector"]
                .get("skip_debt_to_equity_filter", False)
            ):
                financials_mask = (
                    result["sector"]
                    .astype(str)
                    .str.strip()
                    .eq(financials_name)
                )

                non_financials = result.loc[~financials_mask]
                financials = result.loc[financials_mask]

                non_financials = self.apply_filter(
                    non_financials,
                    metric,
                    condition
                )

                result = pd.concat(
                    [non_financials, financials],
                    ignore_index=True
                )

            else:
                result = self.apply_filter(
                    result,
                    metric,
                    condition
                )

        return result

    def run_all(self):
        df = self.build_dataset()

        presets = self.config["presets"]

        results = {}

        for preset_key in presets:
            results[preset_key] = self.apply_preset(
                df,
                preset_key
            )

        return df, results

    def print_summary(self, df, results):
        print("=" * 70)
        print("NIFTY 100 SCREENER ENGINE")
        print("=" * 70)

        print(f"Companies: {df['company_id'].nunique()}")
        print(f"Rows: {len(df)}")

        if "year" in df.columns:
            print(
                "Years:",
                sorted(df["year"].dropna().unique().tolist())
            )

        print(
            "Presets:",
            list(self.config["presets"].keys())
        )

        print(
            "Filterable metrics:",
            len(self.config["filterable_metrics"])
        )

        for col, label in [
            ("market_cap_crore", "Market Cap"),
            ("pe_ratio", "P/E"),
            ("pb_ratio", "P/B"),
            ("dividend_yield_pct", "Dividend Yield"),
        ]:
            if col in df.columns:
                print(
                    f"{label} available:",
                    int(df[col].notna().sum())
                )

        print()

        for key, result in results.items():
            print(
                f"{self.config['presets'][key]['name']}: "
                f"{len(result)} companies"
            )

        print("=" * 70)


if __name__ == "__main__":
    engine = ScreenerEngine()

    df, results = engine.run_all()

    engine.print_summary(df, results)
