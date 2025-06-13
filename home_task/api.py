from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from .db import get_session

router = APIRouter()


@router.get("/days-stats")
def get_days_to_hire_stats(
    standard_job_id: str, country_code: Optional[str] = Query(default=None)
):
    conn = get_session()

    try:
        with conn.begin():
            result = conn.execute(
                text("""
                    SELECT standard_job_id, country_code, min_days, avg_days, max_days, job_postings
                    FROM public.days_to_hire
                    WHERE standard_job_id = :job_id AND country_code IS NOT DISTINCT FROM :cc
                """),
                {"job_id": standard_job_id, "cc": country_code},
            ).fetchone()

            if result is None:
                raise HTTPException(status_code=404, detail="Statistics not found.")

            return {
                "standard_job_id": result["standard_job_id"],
                "country_code": result["country_code"],
                "min_days": result["min_days"],
                "avg_days": result["avg_days"],
                "max_days": result["max_days"],
                "job_postings": result["job_postings"],
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
