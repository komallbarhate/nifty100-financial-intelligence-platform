from pathlib import Path
import csv

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

BASE_DIR = Path(__file__).resolve().parents[3]
STATS_PATH = BASE_DIR / "output" / "portfolio_stats.csv"


@router.get("/stats")
def portfolio_statistics():
    if not STATS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Portfolio statistics file not found",
        )

    with open(STATS_PATH, "r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    return {
        "count": len(rows),
        "statistics": rows,
    }