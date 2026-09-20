from pathlib import Path
import sqlite3

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/peers", tags=["Peers"])

BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "data" / "nifty100.db"


def get_connection():
    if not DB_PATH.exists():
        raise RuntimeError(f"Database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@router.get("/{company_id}")
def peer_comparison(company_id: str):
    """
    Return peer-group comparison for a company using peer_percentiles.
    """

    connection = get_connection()

    try:
        company = connection.execute(
            """
            SELECT
                c.id AS company_id,
                c.company_name,
                pg.peer_group
            FROM companies c
            LEFT JOIN peer_groups pg
                ON c.id = pg.company_id
            WHERE c.id = ?
            """,
            (company_id,),
        ).fetchone()

        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Company not found: {company_id}",
            )

        if not company["peer_group"]:
            return {
                "company_id": company_id,
                "company_name": company["company_name"],
                "peer_group": None,
                "count": 0,
                "peers": [],
            }

        rows = connection.execute(
            """
            SELECT
                pp.company_id,
                c.company_name,
                pp.peer_group,
                pp.metric,
                pp.value,
                pp.percentile_rank,
                pp.year
            FROM peer_percentiles pp
            JOIN companies c
                ON c.id = pp.company_id
            WHERE pp.peer_group = ?
              AND pp.year = (
                  SELECT MAX(pp2.year)
                  FROM peer_percentiles pp2
                  WHERE pp2.peer_group = pp.peer_group
              )
            ORDER BY pp.company_id, pp.metric
            """,
            (company["peer_group"],),
        ).fetchall()

        peer_data = {}

        for row in rows:
            peer_id = row["company_id"]

            if peer_id not in peer_data:
                peer_data[peer_id] = {
                    "company_id": peer_id,
                    "company_name": row["company_name"],
                    "peer_group": row["peer_group"],
                    "year": row["year"],
                    "metrics": {},
                }

            peer_data[peer_id]["metrics"][row["metric"]] = {
                "value": row["value"],
                "percentile_rank": row["percentile_rank"],
            }

        return {
            "company_id": company_id,
            "company_name": company["company_name"],
            "peer_group": company["peer_group"],
            "count": len(peer_data),
            "peers": list(peer_data.values()),
        }

    finally:
        connection.close()