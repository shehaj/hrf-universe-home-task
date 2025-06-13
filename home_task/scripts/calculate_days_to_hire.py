import argparse
import uuid

import numpy as np
from sqlalchemy import text

from home_task.db import get_session


def fetch_standard_job_ids(conn):
    result = conn.execute(
        text("SELECT DISTINCT standard_job_id FROM public.job_posting")
    )
    return [row[0] for row in result]


def fetch_country_codes(conn, job_id):
    result = conn.execute(
        text("""
            SELECT DISTINCT country_code
            FROM public.job_posting
            WHERE standard_job_id = :job_id
        """),
        {"job_id": job_id},
    )
    codes = [row[0] for row in result]
    if None not in codes:
        codes.append(None)
    return codes


def fetch_days_to_hire(conn, job_id, country_code):
    if country_code is None:
        query = """
            SELECT days_to_hire
            FROM public.job_posting
            WHERE standard_job_id = :job_id AND country_code IS NULL
        """
        params = {"job_id": job_id}
    else:
        query = """
            SELECT days_to_hire
            FROM public.job_posting
            WHERE standard_job_id = :job_id AND country_code = :country_code
        """
        params = {"job_id": job_id, "country_code": country_code}

    rows = conn.execute(text(query), params).fetchall()
    return [r[0] for r in rows if r[0] is not None]


def calculate_stats(values):
    if len(values) < 1:
        return None

    values.sort()
    p10 = np.percentile(values, 10)
    p90 = np.percentile(values, 90)

    trimmed = [v for v in values if p10 <= v <= p90]
    if not trimmed:
        return None

    return {
        "min_days": min(trimmed),
        "max_days": max(trimmed),
        "avg_days": round(sum(trimmed) / len(trimmed), 2),
        "count": len(trimmed),
    }


def save_stat(conn, job_id, country_code, stats):
    conn.execute(
        text("""
            INSERT INTO public.days_to_hire (
                id, standard_job_id, country_code, min_days, avg_days, max_days, job_postings
            ) VALUES (
                :id, :job_id, :country_code, :min_days, :avg_days, :max_days, :count
            )
            ON CONFLICT (standard_job_id, country_code)
            DO UPDATE SET
                min_days = EXCLUDED.min_days,
                avg_days = EXCLUDED.avg_days,
                max_days = EXCLUDED.max_days,
                job_postings = EXCLUDED.job_postings
        """),
        {
            "id": str(uuid.uuid4()),
            "job_id": job_id,
            "country_code": country_code,
            "min_days": stats["min_days"],
            "avg_days": stats["avg_days"],
            "max_days": stats["max_days"],
            "count": stats["count"],
        },
    )


def main(threshold):
    conn = get_session()

    try:
        with conn.begin():
            conn.execute(text("DELETE FROM public.days_to_hire"))
            job_ids = fetch_standard_job_ids(conn)

            for job_id in job_ids:
                try:
                    country_codes = fetch_country_codes(conn, job_id)

                    for country_code in country_codes:
                        try:
                            days = fetch_days_to_hire(conn, job_id, country_code)
                            if len(days) < threshold:
                                continue

                            stats = calculate_stats(days)
                            if stats and stats["count"] >= threshold:
                                save_stat(conn, job_id, country_code, stats)

                        except Exception as e:
                            print(f"Skip {job_id} in {country_code}: {e}")
                except Exception as e:
                    print(f"Error for job {job_id}: {e}")

    except Exception as e:
        print(f"Script failed wit error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=int, default=5)
    args = parser.parse_args()

    main(args.threshold)
