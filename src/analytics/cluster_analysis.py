"""
Day 37 — Cluster Profiling & Portfolio Statistics

Outputs:
    output/cluster_profiles.csv
    reports/correlation_heatmap.png
    output/outlier_report.csv
    output/portfolio_stats.csv

Uses the existing Day 36 K-Means cluster assignments.
"""

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "nifty100.db"

CLUSTER_FILE = BASE_DIR / "output" / "cluster_labels.csv"

OUTPUT_DIR = BASE_DIR / "output"
REPORTS_DIR = BASE_DIR / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# KPI DEFINITIONS
# ============================================================

KPI_COLUMNS = [
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "operating_profit_margin_pct",
    "return_on_assets_pct",
    "debt_to_equity",
    "interest_coverage",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "eps_cagr_5yr",
    "fcf_cagr_5yr",
]

KPI_LABELS = {
    "return_on_equity_pct": "ROE (%)",
    "return_on_capital_employed_pct": "ROCE (%)",
    "operating_profit_margin_pct": "OPM (%)",
    "return_on_assets_pct": "ROA (%)",
    "debt_to_equity": "Debt / Equity",
    "interest_coverage": "Interest Coverage",
    "revenue_cagr_5yr": "Revenue CAGR 5Y (%)",
    "pat_cagr_5yr": "PAT CAGR 5Y (%)",
    "eps_cagr_5yr": "EPS CAGR 5Y (%)",
    "fcf_cagr_5yr": "FCF CAGR 5Y (%)",
}


# ============================================================
# DATABASE
# ============================================================

def load_data():
    """Load the required tables from SQLite."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    with sqlite3.connect(DB_PATH) as conn:
        companies = pd.read_sql_query(
            """
            SELECT id, company_name
            FROM companies
            """,
            conn,
        )

        sectors = pd.read_sql_query(
            """
            SELECT company_id, sector, industry
            FROM sectors
            """,
            conn,
        )

        ratios = pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            """,
            conn,
        )

    print(f"Companies loaded: {len(companies)}")
    print(f"Sector records: {len(sectors)}")
    print(f"Ratio records: {len(ratios)}")

    return companies, sectors, ratios


# ============================================================
# FCF CAGR
# ============================================================

def calculate_fcf_cagr(group):
    """
    Calculate 5-year CAGR of free cash flow.

    CAGR requires a positive starting and ending value.
    If the calculation is not mathematically valid, NaN is returned.
    """

    group = group.sort_values("year")

    valid = group[
        group["free_cash_flow_cr"].notna()
    ][["year", "free_cash_flow_cr"]].copy()

    if len(valid) < 2:
        return np.nan

    start_row = valid.iloc[0]
    end_row = valid.iloc[-1]

    start_value = float(start_row["free_cash_flow_cr"])
    end_value = float(end_row["free_cash_flow_cr"])

    start_year = int(start_row["year"])
    end_year = int(end_row["year"])

    years = end_year - start_year

    if years <= 0:
        return np.nan

    if start_value <= 0 or end_value <= 0:
        return np.nan

    return (
        (end_value / start_value) ** (1 / years) - 1
    ) * 100


# ============================================================
# PREPARE LATEST-YEAR DATA
# ============================================================

def prepare_latest_data(companies, sectors, ratios):
    """
    Create one latest-year analytical record per company.

    The function explicitly preserves all KPI columns so that
    downstream cluster profiling cannot lose ratio fields.
    """

    ratios = ratios.copy()

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    for column in KPI_COLUMNS:
        if column in ratios.columns:
            ratios[column] = pd.to_numeric(
                ratios[column],
                errors="coerce",
            )

    ratios["year"] = pd.to_numeric(
        ratios["year"],
        errors="coerce",
    )

    ratios["company_id"] = ratios[
        "company_id"
    ].astype(str)

    companies = companies.copy()
    sectors = sectors.copy()

    companies["id"] = companies["id"].astype(str)
    sectors["company_id"] = sectors["company_id"].astype(str)

    # --------------------------------------------------------
    # Calculate FCF CAGR for every company
    # --------------------------------------------------------

    fcf_cagr = (
        ratios
        .groupby("company_id", group_keys=False)
        .apply(
            calculate_fcf_cagr
        )
        .reset_index(name="fcf_cagr_5yr")
    )

    # --------------------------------------------------------
    # Latest financial-ratio record per company
    # --------------------------------------------------------

    ratios = ratios.sort_values(
        ["company_id", "year"]
    )

    latest = (
        ratios
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    # --------------------------------------------------------
    # Merge FCF CAGR
    # --------------------------------------------------------

    latest = latest.merge(
        fcf_cagr,
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Merge company information
    # --------------------------------------------------------

    latest = latest.merge(
        companies.rename(
            columns={
                "id": "company_id"
            }
        ),
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Merge sector information
    # --------------------------------------------------------

    latest = latest.merge(
        sectors,
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Explicitly verify KPI columns
    # --------------------------------------------------------

    missing = [
        column
        for column in KPI_COLUMNS
        if column not in latest.columns
    ]

    if missing:
        raise ValueError(
            "Required KPI columns missing after data preparation: "
            + ", ".join(missing)
        )

    # --------------------------------------------------------
    # Remove duplicate columns if any
    # --------------------------------------------------------

    latest = latest.loc[
        :,
        ~latest.columns.duplicated()
    ]

    print(
        f"Latest-year company records: {len(latest)}"
    )

    if len(latest) != 92:
        raise ValueError(
            f"Expected 92 latest company records, "
            f"found {len(latest)}"
        )

    return latest


# ============================================================
# LOAD CLUSTERS
# ============================================================

def load_cluster_labels():
    """Load Day 36 K-Means assignments."""

    if not CLUSTER_FILE.exists():
        raise FileNotFoundError(
            f"Cluster labels not found: {CLUSTER_FILE}"
        )

    clusters = pd.read_csv(CLUSTER_FILE)

    required = [
        "company_id",
        "cluster_id",
        "cluster_name",
    ]

    missing = [
        column
        for column in required
        if column not in clusters.columns
    ]

    if missing:
        raise ValueError(
            "Cluster file is missing columns: "
            + ", ".join(missing)
        )

    clusters["company_id"] = (
        clusters["company_id"]
        .astype(str)
    )

    clusters["cluster_id"] = pd.to_numeric(
        clusters["cluster_id"],
        errors="raise",
    ).astype(int)

    print(
        f"Cluster records loaded: {len(clusters)}"
    )

    return clusters


# ============================================================
# MERGE ANALYTICS DATA
# ============================================================

def build_analysis_dataset(latest, clusters):
    """Combine financial metrics with Day 36 cluster assignments."""

    data = latest.merge(
        clusters[
            [
                "company_id",
                "cluster_id",
                "cluster_name",
            ]
        ],
        on="company_id",
        how="inner",
    )

    if len(data) != 92:
        raise ValueError(
            "Cluster merge did not produce 92 companies. "
            f"Found {len(data)}."
        )

    missing_kpis = [
        column
        for column in KPI_COLUMNS
        if column not in data.columns
    ]

    if missing_kpis:
        raise ValueError(
            "KPI columns missing after cluster merge: "
            + ", ".join(missing_kpis)
        )

    return data


# ============================================================
# CLUSTER PROFILES
# ============================================================

def create_cluster_profiles(data):
    """
    Create mean and median profiles for all five clusters.
    """

    rows = []

    for cluster_id in sorted(
        data["cluster_id"].unique()
    ):

        group = data[
            data["cluster_id"] == cluster_id
        ]

        cluster_names = (
            group["cluster_name"]
            .dropna()
            .astype(str)
            .unique()
        )

        cluster_name = (
            cluster_names[0]
            if len(cluster_names) > 0
            else f"Cluster {cluster_id}"
        )

        for metric in KPI_COLUMNS:

            values = pd.to_numeric(
                group[metric],
                errors="coerce",
            )

            rows.append(
                {
                    "cluster_id": int(cluster_id),
                    "cluster_name": cluster_name,
                    "metric": metric,
                    "metric_label": KPI_LABELS.get(
                        metric,
                        metric,
                    ),
                    "mean": values.mean(),
                    "median": values.median(),
                    "company_count": len(group),
                }
            )

    profiles = pd.DataFrame(rows)

    output_path = (
        OUTPUT_DIR
        / "cluster_profiles.csv"
    )

    profiles.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Saved: {output_path}"
    )

    return profiles


# ============================================================
# CORRELATION HEATMAP
# ============================================================

def create_correlation_heatmap(data):
    """Create Pearson correlation heatmap for the 10 KPIs."""

    correlation_data = data[
        KPI_COLUMNS
    ].apply(
        pd.to_numeric,
        errors="coerce",
    )

    correlation = correlation_data.corr(
        method="pearson"
    )

    plt.figure(
        figsize=(14, 11)
    )

    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
        xticklabels=[
            KPI_LABELS[column]
            for column in KPI_COLUMNS
        ],
        yticklabels=[
            KPI_LABELS[column]
            for column in KPI_COLUMNS
        ],
    )

    plt.title(
        "NIFTY 100 Financial KPI Correlation Heatmap",
        fontsize=16,
        pad=15,
    )

    plt.xticks(
        rotation=45,
        ha="right",
    )

    plt.yticks(
        rotation=0
    )

    plt.tight_layout()

    output_path = (
        REPORTS_DIR
        / "correlation_heatmap.png"
    )

    plt.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(
        f"Saved: {output_path}"
    )


# ============================================================
# OUTLIER REPORT
# ============================================================

def create_outlier_report(data):
    """
    Detect sector-level KPI outliers using Z-score.

    Outlier threshold:
        absolute Z-score > 3
    """

    rows = []

    for sector, sector_group in data.groupby(
        "sector",
        dropna=False,
    ):

        sector_group = sector_group.copy()

        for metric in KPI_COLUMNS:

            values = pd.to_numeric(
                sector_group[metric],
                errors="coerce",
            )

            mean = values.mean()
            std = values.std(
                ddof=0
            )

            if pd.isna(std) or std == 0:
                continue

            zscores = (
                values - mean
            ) / std

            for index in zscores[
                zscores.abs() > 3
            ].index:

                rows.append(
                    {
                        "company_id": data.loc[
                            index,
                            "company_id",
                        ],
                        "company_name": data.loc[
                            index,
                            "company_name",
                        ],
                        "sector": sector,
                        "metric": metric,
                        "metric_label": KPI_LABELS.get(
                            metric,
                            metric,
                        ),
                        "value": data.loc[
                            index,
                            metric,
                        ],
                        "sector_mean": mean,
                        "sector_std": std,
                        "z_score": zscores.loc[
                            index
                        ],
                        "abs_z_score": abs(
                            zscores.loc[index]
                        ),
                    }
                )

    outliers = pd.DataFrame(rows)

    if outliers.empty:
        outliers = pd.DataFrame(
            columns=[
                "company_id",
                "company_name",
                "sector",
                "metric",
                "metric_label",
                "value",
                "sector_mean",
                "sector_std",
                "z_score",
                "abs_z_score",
            ]
        )

    outliers = outliers.sort_values(
        "abs_z_score",
        ascending=False,
    )

    output_path = (
        OUTPUT_DIR
        / "outlier_report.csv"
    )

    outliers.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Saved: {output_path}"
    )

    print(
        f"Sector KPI outliers detected: {len(outliers)}"
    )

    return outliers


# ============================================================
# PORTFOLIO STATISTICS
# ============================================================

def create_portfolio_stats(data):
    """
    Calculate portfolio-level percentile statistics
    for every KPI.
    """

    rows = []

    for metric in KPI_COLUMNS:

        values = pd.to_numeric(
            data[metric],
            errors="coerce",
        ).dropna()

        if values.empty:
            continue

        rows.append(
            {
                "metric": metric,
                "metric_label": KPI_LABELS.get(
                    metric,
                    metric,
                ),
                "P10": values.quantile(0.10),
                "P25": values.quantile(0.25),
                "P50": values.quantile(0.50),
                "P75": values.quantile(0.75),
                "P90": values.quantile(0.90),
                "Mean": values.mean(),
                "Std": values.std(),
                "Company_Count": values.count(),
            }
        )

    stats = pd.DataFrame(rows)

    output_path = (
        OUTPUT_DIR
        / "portfolio_stats.csv"
    )

    stats.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Saved: {output_path}"
    )

    return stats


# ============================================================
# PRINT CLUSTER REVIEW
# ============================================================

def print_cluster_review(data):
    """Print a readable summary of the five clusters."""

    print()
    print("=" * 70)
    print("CLUSTER REVIEW")
    print("=" * 70)

    summary = (
        data
        .groupby(
            [
                "cluster_id",
                "cluster_name",
            ]
        )
        .agg(
            company_count=(
                "company_id",
                "nunique",
            ),
            roe_mean=(
                "return_on_equity_pct",
                "mean",
            ),
            debt_equity_mean=(
                "debt_to_equity",
                "mean",
            ),
            revenue_cagr_mean=(
                "revenue_cagr_5yr",
                "mean",
            ),
            fcf_cagr_mean=(
                "fcf_cagr_5yr",
                "mean",
            ),
            opm_mean=(
                "operating_profit_margin_pct",
                "mean",
            ),
        )
        .reset_index()
        .sort_values("cluster_id")
    )

    for _, row in summary.iterrows():

        print()
        print(
            f"Cluster {int(row['cluster_id'])}: "
            f"{row['cluster_name']}"
        )

        print(
            f"  Companies: {int(row['company_count'])}"
        )

        print(
            f"  ROE: {row['roe_mean']:.2f}%"
        )

        print(
            f"  Debt/Equity: "
            f"{row['debt_equity_mean']:.2f}"
        )

        print(
            f"  Revenue CAGR 5Y: "
            f"{row['revenue_cagr_mean']:.2f}%"
        )

        print(
            f"  FCF CAGR 5Y: "
            f"{row['fcf_cagr_mean']:.2f}%"
        )

        print(
            f"  OPM: {row['opm_mean']:.2f}%"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("DAY 37 — CLUSTER PROFILING & STATISTICS")
    print("=" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    companies, sectors, ratios = load_data()

    # --------------------------------------------------------
    # Prepare latest-year financial dataset
    # --------------------------------------------------------

    latest = prepare_latest_data(
        companies,
        sectors,
        ratios,
    )

    # --------------------------------------------------------
    # Load Day 36 clusters
    # --------------------------------------------------------

    clusters = load_cluster_labels()

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    data = build_analysis_dataset(
        latest,
        clusters,
    )

    print(
        f"Analytical records ready: {len(data)}"
    )

    # --------------------------------------------------------
    # Day 37 outputs
    # --------------------------------------------------------

    print()
    print("Creating cluster profiles...")

    profiles = create_cluster_profiles(
        data
    )

    print()
    print("Creating correlation heatmap...")

    create_correlation_heatmap(
        data
    )

    print()
    print("Creating sector outlier report...")

    outliers = create_outlier_report(
        data
    )

    print()
    print("Creating portfolio statistics...")

    portfolio_stats = create_portfolio_stats(
        data
    )

    # --------------------------------------------------------
    # Review
    # --------------------------------------------------------

    print_cluster_review(
        data
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    assert len(data) == 92
    assert data["cluster_id"].nunique() == 5
    assert len(profiles) == 50
    assert len(portfolio_stats) == 10

    print()
    print("=" * 70)
    print("DAY 37 COMPLETE")
    print("=" * 70)

    print(
        "Cluster profiles: output/cluster_profiles.csv"
    )

    print(
        "Correlation heatmap: reports/correlation_heatmap.png"
    )

    print(
        "Outlier report: output/outlier_report.csv"
    )

    print(
        "Portfolio statistics: output/portfolio_stats.csv"
    )

    print(
        f"Outliers detected: {len(outliers)}"
    )


if __name__ == "__main__":
    main()