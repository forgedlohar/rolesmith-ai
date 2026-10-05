import argparse
import asyncio
import json
import uuid

from pydantic import BaseModel

from rolesmith_ai.pipeline.pipeline import RUNS, _background_task, apply_queue, tailor_shortlist
from rolesmith_ai.pipeline.store import get_jobs_by_status

from .llm import LLMError, complete_json
from .pipeline import discover_and_rate
from .profile_store import init_template, sync_into_config
from .settings import settings
from .store import init_db, save_answer


class DummyResponse(BaseModel):
    ok: bool


def cmd_init(args):
    init_db()
    init_template()
    print("Initialized DB and template at ~/.rolesmith_ai/master_profile.json")


def cmd_sync_profile(args):
    sync_into_config()
    print("Synced master profile into config.json")


def cmd_doctor(args):
    print(f"Checking LLM at {settings.llm.base_url} (model {settings.llm.model})...")
    try:
        resp = complete_json("Respond with JSON ok: true", "test", DummyResponse)
        if resp.ok:
            print("LLM is reachable and returning valid JSON.")
        else:
            print("LLM responded but value is not OK.")
    except LLMError as e:
        print(f"LLM Error: {e}")


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


def main():
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

    return 0
