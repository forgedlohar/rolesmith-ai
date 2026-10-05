from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from rolesmith_ai.store import _connect, init_db

init_db()

app = FastAPI(title="Rolesmith AI Dashboard")

static_dir = Path(__file__).parent / "static"

# Mount static files
app.mount("/assets", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    return FileResponse(static_dir / "index.html")


@app.get("/api/stats")
async def get_stats():
    with _connect() as conn:
        total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        total_applied = conn.execute("SELECT COUNT(*) FROM applications WHERE status='applied'").fetchone()[0]

        status_rows = conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall()
        by_status = {r[0]: r[1] for r in status_rows}

        # Latest runs
        runs = conn.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT 5").fetchall()

        return {"total_jobs": total_jobs, "total_applied": total_applied, "by_status": by_status, "recent_runs": [dict(r) for r in runs]}


@app.get("/api/jobs")
async def get_recent_jobs(limit: int = 50):
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT j.url, j.title, j.company, j.platform, j.status, r.score 
            FROM jobs j 
            LEFT JOIN job_ratings r ON j.url = r.job_url
            ORDER BY j.created_at DESC 
            LIMIT ?
        """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def main():
    uvicorn.run("rolesmith_ai.dashboard:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
