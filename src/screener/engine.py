import sqlite3
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
CONFIG_PATH = PROJECT_ROOT / "config" / "screener_config.yaml"


class ScreenerEngine:

    def __init__(
        self,
        db_path: Path = DB_PATH,
        config_path: Path = CONFIG_PATH,
    ):
        self.db_path = Path(db_path)
        self.config_path = Path(config_path)

        self.config = self._load_config()
        self.data = self._load_latest_data()

    def _load_config(self):

        with open(
            self.config_path,
            "r",
            encoding="utf-8",
        ) as file:
            return yaml.safe_load(file)

    def _load_latest_data(self):

        conn = sqlite3.connect(self.db_path)

        ratios = pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            WHERE year = (
                SELECT MAX(fr2.year)
                FROM financial_ratios fr2
                WHERE fr2.company_id = financial_ratios.company_id
            )
            """,
            conn,
        )

        pnl = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                sales,
                net_profit
            FROM profitandloss
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

        market_cap = pd.read_sql_query(
            """
            SELECT *
            FROM market_cap
            WHERE year = (
                SELECT MAX(mc2.year)
                FROM market_cap mc2
                WHERE mc2.company_id = market_cap.company_id
            )
            """,
            conn,
        )

        conn.close()

        # Normalize company identifiers

        for df in [
            ratios,
            pnl,
            companies,
            sectors,
            market_cap,
        ]:

            df["company_id"] = df["company_id"].astype(str).str.strip().str.upper()

        # ---------------------------------------------------------
        # Latest P&L record per company
        # ---------------------------------------------------------

        pnl["year"] = pd.to_numeric(
            pnl["year"],
            errors="coerce",
        )

        pnl = pnl.dropna(
            subset=[
                "company_id",
                "year",
            ]
        )

        pnl = pnl.sort_values(
            [
                "company_id",
                "year",
            ]
        ).drop_duplicates(
            "company_id",
            keep="last",
        )

        # ---------------------------------------------------------
        # Latest market data per company
        # ---------------------------------------------------------

        market_cap["year"] = pd.to_numeric(
            market_cap["year"],
            errors="coerce",
        )

        market_cap = market_cap.dropna(
            subset=[
                "company_id",
                "year",
            ]
        )

        market_cap = market_cap.sort_values(
            [
                "company_id",
                "year",
            ]
        ).drop_duplicates(
            "company_id",
            keep="last",
        )

        # ---------------------------------------------------------
        # Merge data
        # ---------------------------------------------------------

        df = ratios.merge(
            pnl[
                [
                    "company_id",
                    "sales",
                    "net_profit",
                ]
            ],
            on="company_id",
            how="left",
        )

        df = df.merge(
            companies,
            on="company_id",
            how="left",
        )

        df = df.merge(
            sectors,
            on="company_id",
            how="left",
        )

        df = df.merge(
            market_cap[
                [
                    "company_id",
                    "market_cap_crore",
                    "enterprise_value_crore",
                    "pe_ratio",
                    "pb_ratio",
                    "ev_ebitda",
                    "dividend_yield_pct",
                ]
            ],
            on="company_id",
            how="left",
        )

        # ---------------------------------------------------------
        # Numeric conversion
        # ---------------------------------------------------------

        numeric_columns = [
            "return_on_equity_pct",
            "return_on_capital_employed_pct",
            "net_profit_margin_pct",
            "operating_profit_margin_pct",
            "debt_to_equity",
            "interest_coverage",
            "asset_turnover",
            "free_cash_flow_cr",
            "revenue_cagr_5yr",
            "pat_cagr_5yr",
            "eps_cagr_5yr",
            "cfo_pat_ratio",
            "sales",
            "net_profit",
            "earnings_per_share",
            "market_cap_crore",
            "enterprise_value_crore",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield_pct",
            "dividend_payout_ratio_pct",
            "composite_quality_score",
        ]

        for column in numeric_columns:

            if column in df.columns:

                df[column] = pd.to_numeric(
                    df[column],
                    errors="coerce",
                )

        # ---------------------------------------------------------
        # Debt-free handling
        # ---------------------------------------------------------

        if "icr_label" in df.columns:

            df["is_debt_free"] = (
                df["icr_label"].astype(str).str.strip().str.lower().eq("debt free")
            )

        else:

            df["is_debt_free"] = False

        df["icr_for_filter"] = df["interest_coverage"]

        df.loc[
            df["is_debt_free"],
            "icr_for_filter",
        ] = float("inf")

        # ---------------------------------------------------------
        # Financials identification
        # ---------------------------------------------------------

        df["is_financials"] = (
            df["sector"].astype(str).str.strip().str.lower().eq("financials")
        )

        # ---------------------------------------------------------
        # Debt declining flag
        # ---------------------------------------------------------

        df["debt_to_equity_declining"] = self._calculate_debt_decline_flags(
            df["company_id"].tolist()
        )

        # ---------------------------------------------------------
        # Final latest-year dataset
        # ---------------------------------------------------------

        df["year"] = pd.to_numeric(
            df["year"],
            errors="coerce",
        )

        df = (
            df.sort_values(
                [
                    "company_id",
                    "year",
                ]
            )
            .drop_duplicates(
                "company_id",
                keep="last",
            )
            .reset_index(drop=True)
        )

        return df

    def _calculate_debt_decline_flags(
        self,
        company_ids,
    ):

        conn = sqlite3.connect(self.db_path)

        history = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                debt_to_equity
            FROM financial_ratios
            ORDER BY
                company_id,
                year
            """,
            conn,
        )

        conn.close()

        history["company_id"] = (
            history["company_id"].astype(str).str.strip().str.upper()
        )

        history["year"] = pd.to_numeric(
            history["year"],
            errors="coerce",
        )

        history["debt_to_equity"] = pd.to_numeric(
            history["debt_to_equity"],
            errors="coerce",
        )

        result = {}

        for company_id in company_ids:

            company_history = history[history["company_id"] == company_id].dropna(
                subset=["year"]
            )

            company_history = company_history.sort_values("year").drop_duplicates(
                "year",
                keep="last",
            )

            if len(company_history) < 2:

                result[company_id] = False
                continue

            latest = company_history.iloc[-1]["debt_to_equity"]

            previous = company_history.iloc[-2]["debt_to_equity"]

            result[company_id] = (
                pd.notna(latest) and pd.notna(previous) and latest < previous
            )

        return pd.Series(
            [
                result.get(
                    company_id,
                    False,
                )
                for company_id in company_ids
            ]
        )

    @staticmethod
    def _numeric_series(
        df,
        column,
    ):

        return pd.to_numeric(
            df[column],
            errors="coerce",
        )

    def _apply_single_filter(
        self,
        df,
        metric,
        condition,
    ):

        # Turnaround Watch debt decline

        if metric == "debt_to_equity_declining":

            return df[metric].eq(condition.get("equals"))

        actual_metric = metric

        # ICR Debt Free = infinity

        if metric == "interest_coverage":

            actual_metric = "icr_for_filter"

        if actual_metric not in df.columns:

            raise ValueError(f"Required screener metric " f"'{metric}' is unavailable.")

        series = self._numeric_series(
            df,
            actual_metric,
        )

        mask = pd.Series(
            True,
            index=df.index,
        )

        # Minimum

        if "min" in condition:

            mask &= series >= float(condition["min"])

        # Maximum

        if "max" in condition:

            maximum = float(condition["max"])

            # Financial companies skip D/E filter

            if metric == "debt_to_equity":

                mask &= df["is_financials"] | (series <= maximum)

            else:

                mask &= series <= maximum

        return mask.fillna(False)

    def apply_filters(
        self,
        filters: dict | None = None,
        sort_by="composite_quality_score",
        ascending=False,
    ):
        """Apply filters."""
        result = self.data.copy()

        if filters is None:

            filters = {}

        for metric, condition in filters.items():

            mask = self._apply_single_filter(
                result,
                metric,
                condition,
            )

            result = result.loc[mask].copy()

        if sort_by in result.columns:

            result = result.sort_values(
                sort_by,
                ascending=ascending,
                na_position="last",
            )

        return result.reset_index(drop=True)

    def apply_preset(
        self,
        preset_name,
    ):
        """Apply preset."""
        presets = self.config["presets"]

        if preset_name not in presets:

            raise ValueError(f"Unknown preset: " f"{preset_name}")

        return self.apply_filters(presets[preset_name]["filters"])

    def list_presets(self):
        """Process list presets."""
        return {key: value["name"] for key, value in self.config["presets"].items()}

    def available_metrics(self):
        """Process available metrics."""
        return [
            metric
            for metric in self.config["filterable_metrics"]
            if metric in self.data.columns
        ]

    def summary(self):
        """Process summary."""
        return {
            "companies": int(self.data["company_id"].nunique()),
            "rows": len(self.data),
            "years": sorted(self.data["year"].dropna().astype(int).unique().tolist()),
            "presets": list(self.list_presets().keys()),
            "filterable_metrics": len(self.config["filterable_metrics"]),
            "market_cap_available": int(self.data["market_cap_crore"].notna().sum()),
            "pe_available": int(self.data["pe_ratio"].notna().sum()),
            "pb_available": int(self.data["pb_ratio"].notna().sum()),
            "dividend_yield_available": int(
                self.data["dividend_yield_pct"].notna().sum()
            ),
        }


def main():
    """Run the main workflow."""
    print("=" * 70)
    print("NIFTY 100 SCREENER ENGINE")
    print("=" * 70)

    engine = ScreenerEngine()

    summary = engine.summary()

    print(f"Companies: " f"{summary['companies']}")

    print(f"Rows: " f"{summary['rows']}")

    print(f"Years: " f"{summary['years']}")

    print(f"Presets: " f"{summary['presets']}")

    print(f"Filterable metrics: " f"{summary['filterable_metrics']}")

    print(f"Market Cap available: " f"{summary['market_cap_available']}")

    print(f"P/E available: " f"{summary['pe_available']}")

    print(f"P/B available: " f"{summary['pb_available']}")

    print(f"Dividend Yield available: " f"{summary['dividend_yield_available']}")

    print()
    print("Quality Compounder preview:")

    result = engine.apply_preset("quality_compounder")

    columns = [
        "company_id",
        "year",
        "return_on_equity_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
        "composite_quality_score",
    ]

    print(result[columns].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
