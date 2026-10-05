#!/usr/bin/env python3
"""
rolesmith_ai  —  MCP server that automates job searching and applying
across LinkedIn, Naukri, Wellfound, Indeed India, and Hirist.

Transport: stdio  (for Claude Desktop integration)
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from rolesmith_ai.branding import APP_NAME
from rolesmith_ai.pipeline.pipeline import RUNS, start_background
from rolesmith_ai.store import get_application_summary, get_jobs_by_status, save_answer
from rolesmith_ai.tools.apply import apply_job, bulk_apply
from rolesmith_ai.tools.search import filter_jobs, search_jobs
from rolesmith_ai.tools.session import SUPPORTED_PLATFORMS, interactive_login

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,  # MCP stdio uses stdout for protocol — log to stderr
)
logger = logging.getLogger("rolesmith_ai")

server = Server(APP_NAME)

# ---------------------------------------------------------------------------
# Tool catalogue
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="search_jobs",
        description=(
            "Search for DevOps / AI-ML / MLOps jobs across LinkedIn, Naukri, "
            "Wellfound, Indeed India, and Hirist simultaneously using browser "
            "automation.  Returns job listings ranked by relevance to the "
            "embedded candidate profile."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": ("Search keywords. Defaults to the candidate's target roles if omitted."),
                },
                "location": {
                    "type": "string",
                    "default": "India",
                    "description": "Location filter for the search.",
                },
                "experience_years": {
                    "type": "integer",
                    "default": 3,
                    "description": "Minimum years of experience.",
                },
                "remote": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, prefer remote positions.",
                },
                "platforms": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": list(SUPPORTED_PLATFORMS),
                    },
                    "description": ('Which platforms to search. Defaults to all 5. Example: ["naukri", "linkedin"]'),
                },
                "days": {
                    "type": "integer",
                    "default": 30,
                    "description": ("Only return jobs posted within this many days. On LinkedIn this uses its own server-side recency filter, so days=1 means 'past 24 hours'."),
                },
                "fetch_jd": {
                    "type": "boolean",
                    "default": True,
                    "description": (
                        "LinkedIn only. If true, opens each top candidate to "
                        "read the full job description and re-score against "
                        "it — more accurate but adds minutes per search. Set "
                        "false for a fast run that relies on the title gate."
                    ),
                },
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="filter_jobs",
        description=("Filter and rank a list of jobs (from search_jobs) by match score against the candidate profile.  Excludes roles in the avoid list and returns the top 20."),
        inputSchema={
            "type": "object",
            "properties": {
                "jobs": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Job list returned by search_jobs.",
                },
                "min_match_score": {
                    "type": "number",
                    "default": 0.7,
                    "description": "Minimum relevance score (0.0 – 1.0).",
                },
            },
            "required": ["jobs"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="apply_job",
        description=("Apply to a single job via browser automation.  Handles login sessions, fills standard fields, and uploads the resume.  Detects CAPTCHAs and notifies the user."),
        inputSchema={
            "type": "object",
            "properties": {
                "job_url": {
                    "type": "string",
                    "description": "Direct URL to the job posting.",
                },
                "platform": {
                    "type": "string",
                    "enum": list(SUPPORTED_PLATFORMS),
                    "description": "Which platform the job is on.",
                },
                "cover_note": {
                    "type": "string",
                    "default": "",
                    "description": "Optional cover note / message.",
                },
            },
            "required": ["job_url", "platform"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="bulk_apply",
        description=("Apply to multiple jobs in sequence with rate-limiting (30–60 s delay).  Skips already-applied jobs.  Use dry_run=true to preview without actually applying."),
        inputSchema={
            "type": "object",
            "properties": {
                "jobs": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Job list (from search_jobs / filter_jobs).",
                },
                "max_applications": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of applications to submit.",
                },
                "dry_run": {
                    "type": "boolean",
                    "default": True,
                    "description": "Preview mode — no real applications.",
                },
                "max_per_company": {
                    "type": "integer",
                    "default": 2,
                    "description": (
                        "Cap applications to any one company (default 2). "
                        "Counts applications already recorded in the last "
                        "company_window_days, so the cap holds across "
                        "consecutive batches instead of resetting each run."
                    ),
                },
                "company_window_days": {
                    "type": "integer",
                    "default": 1,
                    "description": ("Look-back window for the per-company cap. Default 1 day = 'per session'. Raise it to spread applications to the same employer over a longer period."),
                },
            },
            "required": ["jobs"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_application_status",
        description=("Retrieve tracked applications from the local database, grouped by platform and status (applied, viewed, responded, rejected)."),
        inputSchema={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "default": 7,
                    "description": "Look back this many days.",
                },
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="save_session",
        description=("Open a visible browser window so you can manually log in to a job platform.  The authenticated cookies are saved for future automated use."),
        inputSchema={
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": list(SUPPORTED_PLATFORMS),
                    "description": "Platform to log in to.",
                },
            },
            "required": ["platform"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="pipeline_start",
        description="Start an autopilot run (discover, rate, tailor, apply).",
        inputSchema={
            "type": "object",
            "properties": {
                "auto_apply": {"type": "boolean", "default": False},
                "dry_run": {"type": "boolean", "default": True},
            },
        },
    ),
    Tool(
        name="pipeline_status",
        description="Check status of an autopilot run_id.",
        inputSchema={
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
            },
            "required": ["run_id"],
        },
    ),
    Tool(
        name="list_shortlist",
        description="List all jobs that passed rating and are ready to apply/tailor.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="tailor_resume_for_job",
        description="Tailor resume for a specific job URL.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_url": {"type": "string"},
            },
            "required": ["job_url"],
        },
    ),
    Tool(
        name="apply_shortlist",
        description="Apply to all tailored jobs.",
        inputSchema={
            "type": "object",
            "properties": {
                "auto_apply": {"type": "boolean", "default": False},
                "dry_run": {"type": "boolean", "default": True},
            },
        },
    ),
    Tool(
        name="review_form_answers",
        description="Write a manual override for a form question answer.",
        inputSchema={
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "answer": {"type": "string"},
            },
            "required": ["question", "answer"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    logger.info("Tool called: %s  args=%s", name, json.dumps(arguments, default=str)[:500])

    try:
        if name == "search_jobs":
            result = await search_jobs(
                keywords=arguments.get("keywords"),
                location=arguments.get("location", "India"),
                experience_years=arguments.get("experience_years", 3),
                remote=arguments.get("remote", False),
                platforms=arguments.get("platforms"),
                days=arguments.get("days", 30),
                fetch_jd=arguments.get("fetch_jd", True),
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "jobs_found": len(result),
                            "jobs": result,
                        },
                        indent=2,
                    ),
                )
            ]

        elif name == "filter_jobs":
            result = filter_jobs(
                jobs=arguments["jobs"],
                min_match_score=arguments.get("min_match_score", 0.7),
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "filtered_count": len(result),
                            "jobs": result,
                        },
                        indent=2,
                    ),
                )
            ]

        elif name == "apply_job":
            res_apply = await apply_job(
                job_url=arguments["job_url"],
                platform=arguments["platform"],
                cover_note=arguments.get("cover_note", ""),
            )
            return [TextContent(type="text", text=json.dumps(res_apply, indent=2))]

        elif name == "bulk_apply":
            res_bulk = await bulk_apply(
                jobs=arguments["jobs"],
                max_applications=arguments.get("max_applications", 10),
                dry_run=arguments.get("dry_run", True),
                max_per_company=arguments.get("max_per_company", 2),
                company_window_days=arguments.get("company_window_days", 1),
            )
            return [TextContent(type="text", text=json.dumps(res_bulk, indent=2))]

        elif name == "get_application_status":
            res_status = get_application_summary(
                days=arguments.get("days", 7),
            )
            return [TextContent(type="text", text=json.dumps(res_status, indent=2, default=str))]

        elif name == "save_session":
            res_session = await interactive_login(
                platform=arguments["platform"],
            )
            return [TextContent(type="text", text=json.dumps(res_session, indent=2))]

        elif name == "pipeline_start":
            run_id = start_background(
                "run_pipeline",
                auto_apply=arguments.get("auto_apply", False),
                dry_run=arguments.get("dry_run", True),
            )
            return [TextContent(type="text", text=json.dumps({"run_id": run_id}, indent=2))]

        elif name == "pipeline_status":
            run_id = arguments["run_id"]
            if run_id in RUNS:
                return [TextContent(type="text", text=json.dumps(RUNS[run_id], indent=2))]
            return [TextContent(type="text", text=json.dumps({"error": "Unknown run_id"}))]

        elif name == "list_shortlist":
            jobs = get_jobs_by_status("rated")
            return [TextContent(type="text", text=json.dumps(jobs, indent=2))]

        elif name == "tailor_resume_for_job":
            run_id = start_background("tailor_shortlist", force_url=arguments["job_url"])
            return [TextContent(type="text", text=json.dumps({"run_id": run_id}, indent=2))]

        elif name == "apply_shortlist":
            run_id = start_background("apply_shortlist", dry_run=arguments.get("dry_run", True))
            return [TextContent(type="text", text=json.dumps({"run_id": run_id}, indent=2))]

        elif name == "review_form_answers":
            save_answer(arguments["question"], None, arguments["answer"], "user", 1.0)
            return [TextContent(type="text", text=json.dumps({"status": "saved"}, indent=2))]

        else:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {name}"}),
                )
            ]

    except Exception as exc:
        logger.exception("Tool %s failed", name)
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": str(exc)}),
            )
        ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    def handle_sigterm(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    logger.info("Starting rolesmith_ai server (stdio transport)")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
