import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

DB_PATH = Path("data/nifty100.db")
OUTPUT_DIR = Path("output")
REPORTS_DIR = Path("reports")

OUTPUT_FILE = OUTPUT_DIR / "cluster_labels.csv"
ELBOW_FILE = REPORTS_DIR / "elbow_plot.png"


FEATURE_COLUMNS = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]


def load_data():
    """Load company, sector, ratio, and cash-flow data from SQLite."""
    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query(
        """
        SELECT id AS company_id, company_name
        FROM companies
        """,
        conn,
    )

    sectors = pd.read_sql_query(
        """
        SELECT company_id, sector
        FROM sectors
        """,
        conn,
    )

    ratios = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            return_on_equity_pct,
            debt_to_equity,
            revenue_cagr_5yr,
            operating_profit_margin_pct,
            free_cash_flow_cr
        FROM financial_ratios
        ORDER BY company_id, year
        """,
        conn,
    )

    conn.close()

    return companies, sectors, ratios


def calculate_fcf_cagr(group):
    """Calculate 5-year FCF CAGR from the available historical FCF values."""
    group = group.sort_values("year").copy()

    values = group[["year", "free_cash_flow_cr"]].dropna()

    if len(values) < 2:
        return np.nan

    latest = values.iloc[-1]
    target_year = latest["year"] - 5

    previous = values[values["year"] <= target_year]

    if previous.empty:
        return np.nan

    previous = previous.iloc[-1]

    start_value = previous["free_cash_flow_cr"]
    end_value = latest["free_cash_flow_cr"]
    years = latest["year"] - previous["year"]

    if years <= 0:
        return np.nan

    if start_value <= 0 or end_value <= 0:
        return np.nan

    return ((end_value / start_value) ** (1 / years) - 1) * 100


def prepare_latest_data(companies, sectors, ratios):
    """Prepare one latest-year feature record for every company."""
    latest = (
        ratios.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    fcf_cagr = (
        ratios.groupby("company_id", group_keys=False)
        .apply(calculate_fcf_cagr, include_groups=False)
        .rename("fcf_cagr_5yr")
        .reset_index()
    )

    fcf_cagr.columns = ["company_id", "fcf_cagr_5yr"]

    data = latest.merge(
        fcf_cagr,
        on="company_id",
        how="left",
    )

    data = data.merge(
        sectors.drop_duplicates("company_id"),
        on="company_id",
        how="left",
    )

    data = data.merge(
        companies,
        on="company_id",
        how="left",
    )

    return data


def impute_sector_medians(data):
    """Impute missing clustering features using sector medians."""
    data = data.copy()

    for feature in FEATURE_COLUMNS:
        data[feature] = pd.to_numeric(data[feature], errors="coerce")

        sector_median = data.groupby("sector")[feature].transform("median")

        data[feature] = data[feature].fillna(sector_median)

        overall_median = data[feature].median()

        data[feature] = data[feature].fillna(overall_median)

    return data


def generate_elbow_plot(X_scaled):
    """Generate the KMeans elbow plot for k values 2 through 10."""
    inertias = []

    for k in range(2, 11):
        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10,
        )

        model.fit(X_scaled)
        inertias.append(model.inertia_)

    plt.figure(figsize=(10, 6))
    plt.plot(range(2, 11), inertias, marker="o")
    plt.xticks(range(2, 11))
    plt.xlabel("Number of Clusters (k)")
    plt.ylabel("Inertia")
    plt.title("KMeans Elbow Plot")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    ELBOW_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(ELBOW_FILE, dpi=150)
    plt.close()

    return inertias


def assign_cluster_names(cluster_profiles):
    """Assign descriptive names based on relative cluster feature profiles."""
    profiles = cluster_profiles.copy()

    profiles["quality_score"] = (
        profiles["return_on_equity_pct"].rank(pct=True)
        + profiles["revenue_cagr_5yr"].rank(pct=True)
        + profiles["fcf_cagr_5yr"].rank(pct=True)
        + profiles["operating_profit_margin_pct"].rank(pct=True)
        - profiles["debt_to_equity"].rank(pct=True)
    )

    profiles = profiles.sort_values("quality_score")

    cluster_ids = profiles.index.tolist()

    names = [
        "Distressed or Turnaround",
        "Value Cyclicals",
        "Defensive Dividend Payers",
        "Emerging Growth",
        "High-Quality Compounders",
    ]

    mapping = {}

    for cluster_id, name in zip(cluster_ids, names):
        mapping[cluster_id] = name

    return mapping


def run_clustering():
    """Run the complete KMeans clustering workflow."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("DAY 36 — KMEANS CLUSTERING")
    print("=" * 70)

    companies, sectors, ratios = load_data()

    print(f"Companies loaded: {len(companies)}")
    print(f"Sector records: {len(sectors)}")
    print(f"Ratio records: {len(ratios)}")

    data = prepare_latest_data(
        companies,
        sectors,
        ratios,
    )

    print(f"Latest company records: {len(data)}")

    missing_companies = sorted(set(companies["company_id"]) - set(data["company_id"]))

    if missing_companies:
        print("ERROR: Companies missing from clustering data:")
        print(missing_companies)
        raise RuntimeError("Not all companies have clustering records.")

    data = impute_sector_medians(data)

    remaining_missing = data[FEATURE_COLUMNS].isna().sum()

    print()
    print("Remaining missing values:")
    print(remaining_missing)

    if remaining_missing.sum() > 0:
        raise RuntimeError("Missing values remain after sector-median imputation.")

    X = data[FEATURE_COLUMNS].copy()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print()
    print("Generating elbow plot...")
    inertias = generate_elbow_plot(X_scaled)

    print()
    print("Elbow inertia values:")
    for k, inertia in zip(range(2, 11), inertias):
        print(f"k={k}: {inertia:.4f}")

    model = KMeans(
        n_clusters=5,
        random_state=42,
        n_init=10,
    )

    cluster_ids = model.fit_predict(X_scaled)

    distances = np.linalg.norm(
        X_scaled - model.cluster_centers_[cluster_ids],
        axis=1,
    )

    data["cluster_id"] = cluster_ids
    data["distance_from_centroid"] = distances

    cluster_profiles = data.groupby("cluster_id")[FEATURE_COLUMNS].mean()

    cluster_names = assign_cluster_names(cluster_profiles)

    data["cluster_name"] = data["cluster_id"].map(cluster_names)

    output = data[
        [
            "company_id",
            "cluster_id",
            "cluster_name",
            "distance_from_centroid",
        ]
    ].copy()

    output = output.sort_values("company_id")

    output.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("=" * 70)
    print("CLUSTER SUMMARY")
    print("=" * 70)

    summary = (
        output.groupby(
            ["cluster_id", "cluster_name"],
            as_index=False,
        )
        .size()
        .rename(columns={"size": "company_count"})
        .sort_values("cluster_id")
    )

    print(summary.to_string(index=False))

    print()
    print("Cluster profiles:")
    print(cluster_profiles.round(2).to_string())

    print()
    print(f"Cluster labels saved: {OUTPUT_FILE}")
    print(f"Elbow plot saved: {ELBOW_FILE}")
    print(f"Companies clustered: {len(output)}")
    print(f"Unique clusters: {output['cluster_id'].nunique()}")

    if len(output) != 92:
        raise RuntimeError(f"Expected 92 companies, but clustered {len(output)}.")

    if output["cluster_id"].nunique() != 5:
        raise RuntimeError("Expected exactly 5 clusters.")

    if output["cluster_name"].isna().any():
        raise RuntimeError("Some companies have no cluster name.")

    print()
    print("DAY 36 CLUSTERING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_clustering()
