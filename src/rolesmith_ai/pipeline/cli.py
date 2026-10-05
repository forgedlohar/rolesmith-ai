import argparse
import asyncio
import json
import logging
import subprocess
import sys
import uuid

from pydantic import BaseModel

from rolesmith_ai.pipeline.pipeline import RUNS, _background_task, apply_queue, tailor_shortlist
from rolesmith_ai.store import get_job, get_jobs_by_status, init_db, save_answer, upsert_job
from rolesmith_ai.tools.gmail import check_job_emails, draft_followups
from rolesmith_ai.tools.session import interactive_login

from .llm import complete_json
from .pipeline import discover_and_rate
from .profile_store import init_template, sync_into_config
from .settings import settings


class DummyResponse(BaseModel):
    ok: bool


def cmd_init(args):
    init_db()
    init_template()
    print("Initialized DB and template at ~/.rolesmith_ai/master_profile.json")


def cmd_sync_profile(args):
    sync_into_config()
    print("Synced master profile into config.json")


def check_doctor():
    # 1. Check LLM
    try:
        resp = complete_json("Respond with JSON ok: true", "test", DummyResponse)
        if not resp.ok:
            raise Exception("LLM responded but value is not OK.")
    except Exception as e:
        raise Exception(f"LLM Error: {e}")

    # 2. Check DB
    try:
        get_jobs_by_status("new")
    except Exception as e:
        raise Exception(f"DB Error: {e}")

    # 3. Check Playwright
    try:
        # Just check if playwright executable is found and browsers are installed
        subprocess.run(["uv", "run", "playwright", "--version"], check=True, capture_output=True)
    except Exception as e:
        raise Exception(f"Playwright Error: {e}")


def cmd_doctor(args):
    print("Running Doctor Checks...")
    try:
        check_doctor()
        print("All checks passed. You are ready to run.")
    except Exception as e:
        print(f"Check failed: {e}")
        sys.exit(1)


def cmd_discover(args):
    run_id = str(uuid.uuid4())
    RUNS[run_id] = {"log": []}

    if args.platforms:
        settings.pipeline.platforms = args.platforms.split(",")
    if args.days:
        settings.pipeline.days = args.days
    if args.max_rate:
        settings.pipeline.max_rate_per_run = args.max_rate
    if args.fetch_jd:
        settings.pipeline.fetch_jd_linkedin = True

    asyncio.run(discover_and_rate(run_id))
    for line in RUNS[run_id]["log"]:
        print(line)


def cmd_run(args):
    print("Running doctor checks before starting automation...")
    try:
        check_doctor()
    except Exception as e:
        print(f"Startup check failed: {e}")
        return

    run_id = str(uuid.uuid4())
    asyncio.run(_background_task(run_id, "run_pipeline", auto_apply=args.auto_apply, dry_run=not args.live))
    for line in RUNS[run_id]["log"]:
        print(line)


def cmd_shortlist(args):
    jobs = get_jobs_by_status("rated")
    for j in jobs:
        rating = json.loads(j["rating_json"])
        print(f"Score: {j['llm_score']} | Quality: {rating.get('jd_quality')} | {j['company']} - {j['title']} | {j['url']}")


def cmd_tailor(args):
    run_id = str(uuid.uuid4())
    RUNS[run_id] = {"log": []}
    asyncio.run(tailor_shortlist(run_id))
    for line in RUNS[run_id]["log"]:
        print(line)


def cmd_apply(args):
    run_id = str(uuid.uuid4())
    RUNS[run_id] = {"log": []}
    asyncio.run(apply_queue(run_id, auto_apply=args.auto_apply, dry_run=not args.live))
    for line in RUNS[run_id]["log"]:
        print(line)


def cmd_answers(args):
    if args.set:
        key_val = args.set
        if len(key_val) != 2:
            print("--set requires KEY VALUE")
            return
        question, answer = key_val
        save_answer(question, None, answer, "user", 1.0)
        print(f"Saved override for '{question}': '{answer}'")
    else:
        print("Use --set 'Question' 'Answer'")


def cmd_approve(args):
    url = args.url
    job = get_job(url)
    if not job:
        print(f"Job not found for URL: {url}")
        return
    if job["status"] != "review_needed":
        print(f"Job status is {job['status']}, not review_needed.")
        return
    upsert_job(url, status="approved")
    print(f"Approved job {job['company']} - {job['title']}")


def cmd_login(args):
    asyncio.run(interactive_login(args.platform))


def cmd_check_emails(args):
    print("Checking Gmail for job emails and drafting replies...")
    res = check_job_emails()
    print(json.dumps(res, indent=2))


def cmd_followup(args):
    print("Checking database for old applications and drafting follow-ups...")
    res = draft_followups()
    print(json.dumps(res, indent=2))


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    parser = argparse.ArgumentParser(prog="rolesmith-ai")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")
    subparsers.add_parser("sync-profile")
    subparsers.add_parser("doctor")

    p_disc = subparsers.add_parser("discover")
    p_disc.add_argument("--platforms", type=str)
    p_disc.add_argument("--days", type=int)
    p_disc.add_argument("--max-rate", type=int)
    p_disc.add_argument("--fetch-jd", action="store_true")

    p_run = subparsers.add_parser("run")
    p_run.add_argument("--live", action="store_true")
    p_run.add_argument("--auto-apply", action="store_true")

    subparsers.add_parser("shortlist")

    subparsers.add_parser("tailor")

    p_app = subparsers.add_parser("apply")
    p_app.add_argument("--live", action="store_true")
    p_app.add_argument("--auto-apply", action="store_true")

    p_ans = subparsers.add_parser("answers")
    p_ans.add_argument("--set", nargs=2, metavar=("QUESTION", "ANSWER"))

    p_appr = subparsers.add_parser("approve")
    p_appr.add_argument("url", help="URL of the job to approve")

    p_login = subparsers.add_parser("login")
    p_login.add_argument("platform", help="Platform to login to (e.g. linkedin, naukri)")

    subparsers.add_parser("check-emails")
    subparsers.add_parser("follow-up")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "sync-profile":
        cmd_sync_profile(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "discover":
        cmd_discover(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "shortlist":
        cmd_shortlist(args)
    elif args.command == "tailor":
        cmd_tailor(args)
    elif args.command == "apply":
        cmd_apply(args)
    elif args.command == "answers":
        cmd_answers(args)
    elif args.command == "approve":
        cmd_approve(args)
    elif args.command == "login":
        cmd_login(args)
    elif args.command == "check-emails":
        cmd_check_emails(args)
    elif args.command == "follow-up":
        cmd_followup(args)

    return 0
