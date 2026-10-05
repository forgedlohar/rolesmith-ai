"""
Central database access layer for Rolesmith.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse, urlunparse

from rolesmith_ai.config import DB_PATH, ensure_dirs


def get_db_path() -> str:
    ensure_dirs()
    if DB_PATH.exists():
        DB_PATH.chmod(0o600)
    return str(DB_PATH)


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the schema if it does not exist. (Schema Version 1)"""
    with _connect() as conn:
        conn.execute("PRAGMA user_version = 1;")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                url TEXT PRIMARY KEY,
                norm_url TEXT NOT NULL,
                title TEXT,
                company TEXT,
                platform TEXT,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_norm_url ON jobs(norm_url)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_ratings (
                job_url TEXT PRIMARY KEY,
                score INTEGER,
                verdict TEXT,
                rating_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_url) REFERENCES jobs(url) ON DELETE CASCADE
            )
        """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tailored_resumes (
                job_url TEXT PRIMARY KEY,
                resume_path TEXT,
                cover_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_url) REFERENCES jobs(url) ON DELETE CASCADE
            )
        """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_url TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'applied',
                applied_at TEXT NOT NULL,
                confirmation TEXT,
                error TEXT,
                FOREIGN KEY (job_url) REFERENCES jobs(url) ON DELETE CASCADE
            )
        """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS application_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_url TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT,
                source TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_url) REFERENCES jobs(url) ON DELETE CASCADE
            )
        """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_application_answers_job_url ON application_answers(job_url)")
        # For fast lookup of generic saved answers by hash
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS qa_cache (
                key TEXT PRIMARY KEY,
                answer TEXT,
                source TEXT NOT NULL,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT
            )
        """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS run_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                status TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                error TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
            )
        """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )


def upsert_job(url: str, **kwargs) -> None:
    """Insert or update a job in the pipeline."""
    norm_url = normalize_url(url)

    # Extract data for jobs table
    job_data = {"title": kwargs.get("title"), "company": kwargs.get("company"), "platform": kwargs.get("platform"), "description": kwargs.get("description"), "status": kwargs.get("status", "new")}
    # Filter out None
    job_data = {k: v for k, v in job_data.items() if v is not None}

    with _connect() as conn:
        # Update jobs
        cur = conn.execute("SELECT url FROM jobs WHERE url = ?", (url,))
        if cur.fetchone():
            if job_data:
                updates = [f"{k}=?" for k in job_data]
                updates.append("updated_at=CURRENT_TIMESTAMP")
                q = f"UPDATE jobs SET {', '.join(updates)} WHERE url = ?"
                conn.execute(q, list(job_data.values()) + [url])
        else:
            cols = ["url", "norm_url"] + list(job_data.keys())
            places = ", ".join(["?"] * len(cols))
            vals = [url, norm_url] + list(job_data.values())
            conn.execute(f"INSERT INTO jobs ({', '.join(cols)}) VALUES ({places})", vals)

        # Update ratings if present
        if "llm_score" in kwargs or "verdict" in kwargs or "rating_json" in kwargs:
            conn.execute(
                """
                INSERT INTO job_ratings (job_url, score, verdict, rating_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(job_url) DO UPDATE SET
                    score=excluded.score,
                    verdict=excluded.verdict,
                    rating_json=excluded.rating_json
                """,
                (url, kwargs.get("llm_score"), kwargs.get("verdict"), kwargs.get("rating_json")),
            )

        # Update tailored resumes if present
        if "resume_path" in kwargs or "cover_note" in kwargs:
            conn.execute(
                """
                INSERT INTO tailored_resumes (job_url, resume_path, cover_note)
                VALUES (?, ?, ?)
                ON CONFLICT(job_url) DO UPDATE SET
                    resume_path=excluded.resume_path,
                    cover_note=excluded.cover_note
                """,
                (url, kwargs.get("resume_path"), kwargs.get("cover_note")),
            )

        # Error handling from previous logic
        if "error" in kwargs:
            conn.execute("UPDATE applications SET error = ? WHERE job_url = ?", (kwargs["error"], url))


def get_job(url: str) -> dict[str, Any] | None:
    """Get a comprehensive job dict including ratings and resumes."""
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT j.*, r.score as llm_score, r.verdict, r.rating_json, 
                   t.resume_path, t.cover_note, a.error
            FROM jobs j
            LEFT JOIN job_ratings r ON j.url = r.job_url
            LEFT JOIN tailored_resumes t ON j.url = t.job_url
            LEFT JOIN applications a ON j.url = a.job_url
            WHERE j.url = ?
            """,
            (url,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_jobs_by_status(status: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT j.*, r.score as llm_score, r.verdict, r.rating_json, 
                   t.resume_path, t.cover_note, a.error
            FROM jobs j
            LEFT JOIN job_ratings r ON j.url = r.job_url
            LEFT JOIN tailored_resumes t ON j.url = t.job_url
            LEFT JOIN applications a ON j.url = a.job_url
            WHERE j.status = ?
            """,
            (status,),
        )
        return [dict(r) for r in cur.fetchall()]


# -------------------------------------------------------------------------
# Applications / Tracker functions
# -------------------------------------------------------------------------


def record_application(
    job_title: str,
    company: str,
    platform: str,
    job_url: str,
    status: str = "applied",
    confirmation: str | None = None,
    cover_note: str | None = None,
    match_score: float | None = None,
) -> int:
    """
    Insert an application record, or update the existing one for this job_url.
    Returns the row id.
    """
    upsert_job(job_url, title=job_title, company=company, platform=platform, status=status)
    if cover_note or match_score:
        upsert_job(job_url, cover_note=cover_note, llm_score=match_score)

    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO applications (job_url, status, applied_at, confirmation)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(job_url) DO UPDATE SET
                status=excluded.status,
                applied_at=excluded.applied_at,
                confirmation=excluded.confirmation
            """,
            (
                job_url,
                status,
                datetime.now(timezone.utc).isoformat(),
                confirmation,
            ),
        )
        return cur.lastrowid


def is_already_applied(job_url: str) -> bool:
    """Check if we've successfully applied to this URL."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM applications WHERE job_url = ? AND status = 'applied'",
            (job_url,),
        ).fetchone()
        return row is not None


def count_recent_applications_for_company(company: str, days: int = 1) -> int:
    """How many successful applications went to *company* in the last *days*."""
    if not company or not company.strip():
        return 0
    with _connect() as conn:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        row = conn.execute(
            """
            SELECT COUNT(*) FROM applications a
            JOIN jobs j ON a.job_url = j.url
            WHERE LOWER(TRIM(j.company)) = LOWER(TRIM(?))
              AND a.status = 'applied'
              AND a.applied_at >= ?
            """,
            (company, cutoff),
        ).fetchone()
        return int(row[0]) if row else 0


def update_status(job_url: str, status: str) -> None:
    upsert_job(job_url, status=status)
    with _connect() as conn:
        conn.execute("UPDATE applications SET status = ? WHERE job_url = ?", (status, job_url))


def get_applications(days: int = 7) -> list[dict[str, Any]]:
    """Return applications from the last *days* days."""
    with _connect() as conn:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """
            SELECT a.id, j.title as job_title, j.company, j.platform, a.job_url,
                   a.status, a.applied_at, a.confirmation, r.score as match_score
            FROM applications a
            JOIN jobs j ON a.job_url = j.url
            LEFT JOIN job_ratings r ON j.url = r.job_url
            WHERE a.applied_at >= ?
            ORDER BY a.applied_at DESC
            """,
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_application_summary(days: int = 7) -> dict[str, Any]:
    apps = get_applications(days)
    by_platform: dict[str, dict[str, list[dict]]] = {}
    by_status: dict[str, int] = {}

    for app in apps:
        plat = app["platform"]
        status = app["status"]
        by_platform.setdefault(plat, {}).setdefault(status, []).append(app)
        by_status[status] = by_status.get(status, 0) + 1

    return {
        "total": len(apps),
        "days": days,
        "by_platform": by_platform,
        "by_status": by_status,
    }


# -------------------------------------------------------------------------
# QA Cache
# -------------------------------------------------------------------------


def _qa_key(question: str, options: list[str] | None) -> str:
    norm_q = question.strip().lower()
    if options:
        opts = sorted([o.strip().lower() for o in options])
        norm_q += "|" + "|".join(opts)
    return hashlib.sha1(norm_q.encode("utf-8")).hexdigest()


def get_cached_answer(question: str, options: list[str] | None = None) -> tuple[Any, str, float] | None:
    key = _qa_key(question, options)
    with _connect() as conn:
        cur = conn.execute("SELECT answer, source, confidence FROM qa_cache WHERE key = ?", (key,))
        row = cur.fetchone()
        if row:
            ans, src, conf = row
            try:
                ans = json.loads(ans)
            except Exception:
                pass
            return ans, src, conf
    return None


def save_answer(
    question: str,
    options: list[str] | None,
    answer: Any,
    source: str,
    confidence: float,
):
    key = _qa_key(question, options)
    with _connect() as conn:
        cur = conn.execute("SELECT source FROM qa_cache WHERE key = ?", (key,))
        row = cur.fetchone()
        if row and row[0] == "user" and source != "user":
            return

        ans_str = json.dumps(answer)
        conn.execute(
            """
            INSERT INTO qa_cache (key, answer, source, confidence)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                answer=excluded.answer,
                source=excluded.source,
                confidence=excluded.confidence
            """,
            (key, ans_str, source, confidence),
        )


def log_audit(event_type: str, details: str) -> None:
    with _connect() as conn:
        conn.execute("INSERT INTO audit_log (event_type, details) VALUES (?, ?)", (event_type, details))
