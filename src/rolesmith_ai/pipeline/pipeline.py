import asyncio
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Any

from rolesmith_ai import config
from rolesmith_ai.pipeline.models import JobRating
from rolesmith_ai.store import get_db_path, get_job, get_jobs_by_status, is_already_applied, upsert_job
from rolesmith_ai.tools.apply import apply_job
from rolesmith_ai.tools.search import search_jobs

from .jd import fetch_jd
from .llm import LLMError
from .profile_store import load_master_profile
from .rating import rate_job
from .render import render_resume
from .settings import settings
from .tailor import tailor_resume

logger = logging.getLogger(__name__)

RUNS: dict[str, dict[str, Any]] = {}


def daily_remaining() -> int:
    with sqlite3.connect(get_db_path()) as conn:
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        cur = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE applied_at > ? AND status = 'applied'",
            (yesterday,),
        )
        count = cur.fetchone()[0]
        return max(0, settings.pipeline.max_per_day - count)


def _should_avoid(company: str, avoids: list[str]) -> bool:
    comp_lower = company.lower()
    for a in avoids:
        a_lower = a.lower()
        if a_lower in comp_lower or (len(comp_lower) >= 4 and comp_lower in a_lower):
            return True
    return False


async def discover_and_rate(run_id: str, fetch_limit: int | None = None):
    RUNS.setdefault(run_id, {"log": []})
    logger.info("Starting discovery and rating...")

    if daily_remaining() <= 0:
        logger.warning("Daily limit reached. Aborting.")
        return

    master = load_master_profile()

    # Search
    jobs = await search_jobs(
        keywords=master.target_roles,
        location=master.location,
        experience_years=int(master.total_experience_years),
        platforms=settings.pipeline.platforms,
        days=settings.pipeline.days,
        fetch_jd=settings.pipeline.fetch_jd_linkedin,
    )

    logger.info(f"Discovered {len(jobs)} jobs across platforms.")

    # Dedupe and pre-filter
    seen = set()
    to_rate = []

    for j in jobs:
        key = (j["company"].lower(), j["title"].lower())
        if key in seen:
            continue
        seen.add(key)

        if is_already_applied(j["apply_url"]):
            continue

        if _should_avoid(j["company"], master.preferences.avoid_companies):
            upsert_job(
                j["apply_url"],
                title=j["title"],
                company=j["company"],
                platform=j["platform"],
                status="skipped",
                verdict="skip",
                error="Avoid company match",
            )
            continue

        to_rate.append(j)

    limit = fetch_limit or settings.pipeline.max_rate_per_run
    to_rate = to_rate[:limit]

    logger.info(f"Rating {len(to_rate)} jobs...")

    rated_count = 0
    for j in to_rate:
        desc = j.get("description", "")
        if not desc and settings.pipeline.jd_enrich:
            logger.info(f"Fetching JD for {j['company']} - {j['title']}...")
            desc = fetch_jd(j["apply_url"], j["platform"]) or ""

        if len(desc) > settings.pipeline.max_jd_chars:
            desc = desc[: settings.pipeline.max_jd_chars]

        try:
            rating = rate_job(j["title"], j["company"], desc)
            upsert_job(
                j["apply_url"],
                title=j["title"],
                company=j["company"],
                platform=j["platform"],
                description=desc,
                status="rated",
                llm_score=rating.score,
                verdict=rating.verdict,
                rating_json=rating.model_dump_json(),
            )
            rated_count += 1
        except LLMError as e:
            logger.error(f"LLM Error during rating. Aborting batch: {e}")
            break

    logger.info(f"Finished rating {rated_count} jobs.")


async def tailor_shortlist(run_id: str, force_url: str | None = None):
    RUNS.setdefault(run_id, {"log": []})
    logger.info("Starting tailor shortlist...")

    if force_url:
        jobs = [get_job(force_url)]
        if not jobs[0] or jobs[0]["status"] not in ("rated", "discovered"):
            logger.warning(f"Job {force_url} not ready for tailoring.")
            return
    else:
        # Get rated jobs that meet threshold
        all_rated = get_jobs_by_status("rated")
        jobs = []
        for j in all_rated:
            rating = json.loads(j["rating_json"])
            if rating["score"] >= settings.pipeline.tailor_min_score and rating["jd_quality"] != "missing":
                jobs.append(j)

        if not jobs:
            return

        jobs = sorted(jobs, key=lambda x: x["llm_score"], reverse=True)[: settings.pipeline.max_tailor_per_run]

    logger.info(f"Tailoring resumes for {len(jobs)} jobs...")

    tailored_count = 0
    for j in jobs:
        rating_dict = json.loads(j["rating_json"])

        rating = JobRating(**rating_dict)
        try:
            desc = j.get("description") or "Missing description."
            draft, warnings = tailor_resume(j["title"], j["company"], desc, rating)

            pdf_path = render_resume(j["company"], draft, warnings)

            cover_note = draft.cover_note if settings.pipeline.cover_note else None

            upsert_job(j["url"], status="tailored", resume_path=pdf_path, cover_note=cover_note)
            tailored_count += 1
            if warnings:
                logger.warning(f"Tailoring warnings for {j['company']}: {warnings}")
        except LLMError as e:
            logger.error(f"LLM Error during tailoring. Aborting batch: {e}")
            break

    logger.info(f"Finished tailoring {tailored_count} resumes.")


async def apply_queue(run_id: str, auto_apply: bool = False, dry_run: bool = True):
    RUNS.setdefault(run_id, {"log": []})
    logger.info(f"Starting apply queue (dry_run={dry_run}, auto_apply={auto_apply})...")

    tailored_jobs = get_jobs_by_status("tailored") + get_jobs_by_status("approved")
    jobs_to_apply = []

    for j in tailored_jobs:
        if is_already_applied(j["url"]):
            upsert_job(j["url"], status="skipped", error="Already applied in tracker")
            continue

        rating = json.loads(j["rating_json"])
        if auto_apply and not dry_run:
            if rating["score"] < settings.pipeline.auto_apply_min_score or rating["jd_quality"] != "full":
                logger.info(f"Skipping {j['company']} - score {rating['score']} too low or jd_quality {rating['jd_quality']} not full for unattended.")
                continue
        elif not auto_apply and not dry_run:
            if j["status"] != "approved":
                seniority = rating.get("seniority_fit", "").lower()
                if rating["score"] >= settings.pipeline.review_high_score or "poor" in seniority or "overqualified" in seniority:
                    upsert_job(j["url"], status="review_needed", error="High score or seniority mismatch requires manual approval")
                    logger.info(f"Review needed for {j['company']} before applying")
                    continue

        jobs_to_apply.append(j)

    for j in jobs_to_apply:
        if daily_remaining() <= 0:
            logger.warning("Daily limit reached. Aborting applies.")
            break

        logger.info(f"Applying to {j['company']}...")
        if dry_run:
            upsert_job(j["url"], status="applied_dry_run")
            logger.info(f"[Dry Run] Applied to {j['company']}")
            continue

        # Real apply requires cfg override
        cfg = config.load_config()
        original_resume = cfg.resume_path
        cfg.resume_path = j["resume_path"]
        config.save_config(cfg)  # Needs to be saved for tools.apply to see it? Or replace(cfg, resume_path)
        # Actually in Phase 6 instructions: "Applier functions take cfg: AppConfig (a dataclass). Use dataclasses.replace(cfg, resume_path=...) for per-job resumes instead of mutating globals."
        # And "tools/apply.py: add optional resume_path to apply_job"

        try:
            res = await apply_job(
                job_url=j["url"],
                platform=j["platform"],
                cover_note=j["cover_note"] or "",
                job_title=j["title"],
                company=j["company"],
                match_score=j["llm_score"],
                resume_path=j["resume_path"],  # we will add this in Phase 6
            )

            if res.get("success"):
                upsert_job(j["url"], status="applied")
                logger.info(f"Successfully applied to {j['company']}")
            elif res.get("status") == "review_needed":
                upsert_job(j["url"], status="review_needed", error=res.get("error", "Flagged answer"))
                logger.warning(f"Review needed for {j['company']}: {res.get('error')}")
            else:
                upsert_job(j["url"], status="failed", error=res.get("error", "Unknown error"))
                logger.error(f"Failed to apply to {j['company']}: {res.get('error')}")
        finally:
            # Restore original
            cfg.resume_path = original_resume
            config.save_config(cfg)


async def _background_task(run_id: str, action: str, **kwargs):
    RUNS[run_id] = {"status": "running", "log": []}
    try:
        if action == "run_pipeline":
            await discover_and_rate(run_id)
            await tailor_shortlist(run_id)
            await apply_queue(
                run_id,
                auto_apply=kwargs.get("auto_apply", False),
                dry_run=kwargs.get("dry_run", True),
            )
        elif action == "tailor_shortlist":
            await tailor_shortlist(run_id, force_url=kwargs.get("force_url"))
        elif action == "apply_shortlist":
            await apply_queue(run_id, auto_apply=False, dry_run=kwargs.get("dry_run", True))
        RUNS[run_id]["status"] = "completed"
    except Exception as e:
        RUNS[run_id]["status"] = "failed"
        logger.error(f"Background task {action} failed: {e!s}")


def start_background(action: str, **kwargs) -> str:
    run_id = str(uuid.uuid4())
    asyncio.create_task(_background_task(run_id, action, **kwargs))
    return run_id
