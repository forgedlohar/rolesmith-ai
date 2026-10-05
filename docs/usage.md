# Usage Guide

## Quickstart (Standalone)

You can run Rolesmith AI entirely as a standalone Python CLI without Claude Desktop.

1. Install dependencies with `uv sync`.
2. Setup configuration using `uv run rolesmith-ai init`.
3. Provide your `resume_template.tex` in `~/.rolesmith/`.
4. Run doctor checks to ensure setup is valid:
   ```bash
   uv run rolesmith-ai doctor
   ```
5. Log into target platforms (e.g. LinkedIn) using the interactive login command if needed:
   ```bash
   uv run rolesmith-ai login linkedin
   ```
   (Select Option 1 to store interactive sessions).

## The Autopilot Pipeline

The pipeline operates in three distinct phases, which you can run separately or together.

1. **Discover & Rate**: Finds jobs and scores them using the LLM.
   ```bash
   uv run rolesmith-ai discover --platforms linkedin,wellfound --days 1 --max-rate 20
   ```

2. **Tailor Resumes**: For jobs that pass the minimum score, generates tailored resumes.
   ```bash
   uv run rolesmith-ai tailor
   ```

3. **Apply**: Uses Playwright to execute applications and answer form questions using the LLM.
   ```bash
   # Dry-run mode (Preview applications without submitting)
   uv run rolesmith-ai apply

   # Live mode (Actually submit the application)
   uv run rolesmith-ai apply --live
   ```

4. **Human Review**: If the LLM lacks confidence on an employer question or flags a job for review due to seniority mismatch, the job status is set to `review_needed`. You can manually approve it:
   ```bash
   uv run rolesmith-ai approve "https://linkedin.com/jobs/view/123"
   ```

Or you can run the entire pipeline at once:
```bash
uv run rolesmith-ai run --live --auto-apply
```

## Web Dashboard

You can visualize your job applications, view LLM relevance scores, and explore your pipeline through a local web dashboard.
```bash
make dashboard
```
Open `http://localhost:8000` in your browser.

## Recruiter Communications (Gmail)

Rolesmith AI can securely connect to your Gmail to handle recruiter communications:

1. **Check Emails & Interview Prep**
   ```bash
   make check-emails
   ```
   Scans your inbox for recruiter emails, decides if they require a reply, and saves a drafted response for you. If it's an interview request, it generates a `prep_sheet.md` with company background and likely questions.

2. **Automated Follow-ups**
   ```bash
   make follow-ups
   ```
   Queries your database for jobs applied to more than 7 days ago, and drafts polite follow-up emails in your Gmail.

## Model Context Protocol (MCP)

To use Rolesmith via Claude Desktop, add it to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rolesmith": {
      "command": "uv",
      "args": ["run", "rolesmith_ai-server"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

This exposes tools to Claude like `autopilot_start`, `list_shortlist`, and `review_form_answers`.
