# Rolesmith AI

An LLM "autopilot" pipeline that discovers, rates, and autonomously applies to jobs across multiple platforms, intelligently tailoring your resume per application.

Rolesmith AI builds upon the foundational web automation of `job-apply-mcp`, extending it with a powerful AI agent pipeline that reasons about Job Descriptions, customizes your PDF resume via LaTeX, and completes complex application forms natively in Playwright.

## Features

- **Multi-Platform Automation**: Supports LinkedIn, Naukri, Wellfound, and Indeed India.
- **LLM-Powered Rating**: Evaluates Job Descriptions against your profile to find high-match roles and identify red flags.
- **Beautiful ATS PDF Resumes**: Dynamically compiles and generates gorgeous, tailored PDF resumes on the fly using `reportlab`.
- **Smart Form Completion**: Answers dynamic application form questions accurately using context from your profile and LLM inference.
- **Web Dashboard**: Monitor your job search pipeline, inspect LLM ratings, and review applications visually via `make dashboard`.
- **Gmail Automation & Follow-ups**: Connects to Gmail to detect recruiter emails, intelligently drafts responses, and auto-drafts follow-up emails for applications older than 7 days.
- **Interview Prep**: Instantly generates an Interview Prep Cheat Sheet (company summary, JD, and 5 technical/behavioral questions) when an interview is requested.
- **MCP Integration**: Fully compatible as a Model Context Protocol (MCP) server for Claude Desktop.

## Documentation

- [Configuration Guide](docs/configuration.md)
- [Usage Guide](docs/usage.md)
- [Architecture](docs/architecture.md)

## Installation

We use `uv` for reproducible environment management:

```bash
# Clone the repository
git clone https://github.com/your-username/rolesmith-ai.git
cd rolesmith-ai

# Install dependencies using uv
uv sync
```

For full installation and MCP setup instructions, see the [Usage Guide](docs/usage.md).

## Usage

You can run Rolesmith AI as a standalone CLI or connect it to Claude Desktop as an MCP server.

### Startup Checklist
Before running automation, ensure your setup is ready:
```bash
uv run rolesmith-ai doctor
```

### Automation Lifecycle
Run individual stages or the entire pipeline at once:
```bash
uv run rolesmith-ai discover
uv run rolesmith-ai tailor
uv run rolesmith-ai apply --live
```

### Dashboard & Analytics
Run the sleek web dashboard to track your application metrics, view jobs by status, and monitor LLM ratings:
```bash
make dashboard
```

### Recruiter Communications
Automate your inbox. The following commands scan your Gmail, draft highly contextual replies to recruiters, and draft follow-up emails for unresponsive applications:
```bash
make check-emails
make follow-ups
```
Or run the full pipeline in one command:
```bash
uv run rolesmith-ai run --live --auto-apply
```

### Human-in-the-Loop Review
If a job requires manual approval (due to high seniority, exceptional match score, or an unanswerable question), the pipeline pauses and sets the status to `review_needed`.

Approve jobs to let the pipeline continue:
```bash
uv run rolesmith-ai approve "https://linkedin.com/jobs/view/123"
```

If bot detection is triggered, run the interactive login:
```bash
uv run rolesmith-ai login linkedin
```

## Attribution

Rolesmith AI was originally forked from [pulkit017/job-apply-mcp](https://github.com/pulkit017/job-apply-mcp). The base Playwright automation and MCP transport mechanisms were adapted from the original project. The AI pipeline (discovery, rating, tailoring, and autonomous form completion) was added as a complete autopilot layer on top.
