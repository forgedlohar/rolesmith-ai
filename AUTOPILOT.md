# Autopilot

Autopilot is an LLM-driven layer on top of `job-apply-mcp` that fully automates the job application process: discovering jobs, rating them for fit, tailoring your resume, and applying.

## How it works

The pipeline runs in three stages:

1. **Discover & Rate**: Searches for jobs, fetches the JD, and asks the LLM to score the job against your master profile.
2. **Tailor**: Takes highly-rated jobs and rewrites the resume bullets/summary/headline to match the required skills, dropping any hallucinated or missing skills.
3. **Apply**: Uses the base project's automation to apply using the tailored PDF resume.

## Configuration

Set the environment variables:
- `OPENAI_API_KEY`: Your OpenAI key
- `OPENAI_API_BASE`: (Optional) Custom base URL

Run the doctor command to ensure the LLM is reachable:
```bash
python -m autopilot doctor
```

## Setup

First, initialize your master profile template and database:
```bash
python -m autopilot init
```
This creates `~/.job-apply-mcp/master_profile.json` and a local SQLite DB for autopilot. Edit the master profile with your full experience.

Then, sync it into the base configuration:
```bash
python -m autopilot sync-profile
```

## CLI Usage

Run a full cycle (dry-run by default):
```bash
python -m autopilot run
```
To run an automated run with real applies:
```bash
python -m autopilot run --live --auto-apply
```

List shortlisted jobs:
```bash
python -m autopilot shortlist
```

Tailor resumes for the shortlist:
```bash
python -m autopilot tailor
```

Apply to the tailored jobs:
```bash
python -m autopilot apply
```

Override form answers:
```bash
python -m autopilot answers --set "Are you willing to relocate?" "No"
```

## MCP Integration

The server exposes new tools:
- `autopilot_start`: Trigger an autopilot cycle.
- `autopilot_status`: Check the status of a run.
- `list_shortlist`: See jobs that passed rating.
- `tailor_resume_for_job`: Tailor for a specific job.
- `apply_shortlist`: Apply to all tailored jobs.
- `review_form_answers`: Override form answers.
