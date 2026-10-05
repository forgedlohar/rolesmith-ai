# Rolesmith AI Architecture

Rolesmith AI is a fully automated, LLM-driven job application pipeline. It discovers, rates, tailors, and applies to jobs autonomously, incorporating robust security boundaries and human-in-the-loop oversight.

## Core Components

1. **Crawler (`search.py`)**: Uses Playwright to discover jobs across platforms like LinkedIn, Naukri, Wellfound, Indeed, etc., saving results to a local SQLite database.
2. **LLM Rater (`rating.py`)**: Extracts information from job descriptions and evaluates candidate fit based on a local master profile. Untrusted input (like Job Descriptions) is wrapped in security boundaries (`<UNTRUSTED_JD>`) to prevent prompt injection.
3. **Tailor (`tailor.py` / `render.py`)**: Generates customized resumes and cover notes based on the parsed job requirements. Uses Markdown and Typst for PDF rendering.
4. **Playwright Applier (`apply.py`)**: Automates form filling on various platforms. If answers to arbitrary employer questions cannot be grounded from the user's profile with high confidence (`llm_answers.py`), or if seniority mismatch is detected, the pipeline halts the apply and sets the job to `review_needed`.

## State Flow

1. **`new`**: Job discovered.
2. **`rated`**: Evaluated by the LLM Rater.
3. **`tailored`**: A customized resume has been generated.
4. **`review_needed`**: Manual approval required (due to low LLM confidence on a question, or a seniority/score mismatch).
5. **`approved`**: User approved via CLI (`rolesmith-ai approve <url>`).
6. **`applied`**: Application successfully submitted by the Applier.
7. **`failed` / `skipped`**: Terminated flows.

## Security Boundaries

- **Trust Boundary**: JDs, employer questions, and dropdown options are strictly untrusted. They are enclosed within pseudo-XML tags (`<UNTRUSTED_JD>`, `<UNTRUSTED_QUESTION>`, `<UNTRUSTED_OPTIONS>`) instructing the LLM to ignore injection attempts.
- **File Permissions**: The SQLite database (`jobs.db`) and saved session cookies (`~/.rolesmith/sessions/`) are enforced at `0o600` permissions.
