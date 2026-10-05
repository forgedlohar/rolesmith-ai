# Execution Plan

## Phase 1 - One database, one access layer
1. **Analyze existing stores:** `tools/tracker.py` uses `applications.db` (table: `applications`). `pipeline/store.py` uses `applications.db` (tables: `pipeline_jobs`, `qa_cache`, `audit_log`, `gmail_messages` although currently deleted).
2. **Consolidate:** Create `src/rolesmith_ai/store.py`. Delete `pipeline/store.py` and `tools/tracker.py`. Refactor the rest of the code to use this central module.
3. **Schema Definition:** Implement the requested schema (`jobs`, `job_ratings`, `tailored_resumes`, `applications`, `application_answers`, `runs`, `run_stages`, `audit_log`). Use proper Foreign Keys.
4. **Behavior:** Ensure duplicate prevention and rate-limiting still work with the new schema. Add tests.

## Phase 2 - Trust boundaries and prompt injection
1. **Isolation in LLM calls:** Update prompts in `jd.py`, `rating.py`, `tailor.py`, `llm_answers.py` to wrap untrusted text (like JD and form questions) in delimiters (e.g. `<UNTRUSTED_INPUT>...</UNTRUSTED_INPUT>`). Add clear system instructions to ignore instructions inside these blocks.
2. **No Tools:** Ensure these LLM calls do NOT use tool calling (JSON mode / structured outputs are fine, but no MCP/function-calling capabilities during evaluation).
3. **Validation:** Pydantic validation handles parsing failures.
4. **Testing:** Create tests with prompt injection examples and verify they do not alter application behavior or cause actions.

## Phase 3 - Answer grounding and human approval
1. **Grounding:** Update `llm_answers.py`. The LLM should only use Master Profile, Tailored Resume, and Saved Answers. If unavailable, return "unknown" (flagged).
2. **Hard Rules:** Reject automatic answering for visa, salary, start date, relocation, criminal history, and demographics. These must return "unknown" unless explicitly predefined.
3. **Auditability:** Record answer source and confidence in `application_answers` table.
4. **Review Gate:** Implement a manual review gate for live applies. If any answer is flagged ("unknown"), confidence < threshold, or job is highly rated, stop and require CLI approval.

## Phase 4 - Operational robustness
1. **Doctor command:** Update `cli.py` and `pipeline/pipeline.py` (if doctor is there) to check `pdflatex`, Playwright, config directory permissions (0o600), DB schema version, LLM endpoint.
2. **Session Security:** Document in README. Set 0o600 permissions on `sessions/`. Ensure `.gitignore` ignores `sessions/`.
3. **Logging:** Implement structured logging to DB (`run_stages`, `runs`, `audit_log`) and rotated files. Mask sensitive strings.
4. **Resilience:** Add `tenacity` or custom retry logic for network/LLM calls.
5. **Bot Detection:** Handle captchas and login walls gracefully, marking job as "blocked". Never retry.
6. **Watch Mode:** Add `--watch` to CLI. Provide cron/systemd examples in docs.

## Phase 5 - Documentation
1. **Architecture:** Write `ARCHITECTURE.md` with Mermaid diagrams, trust boundaries, state machines, etc.
2. **Updates:** Clean up `README.md`, `AUTOPILOT.md`, and `STATE.md`.
3. **Makefile:** Add targets for `test`, `lint`, `doctor`.
4. **Final Report:** Document all changes, design decisions, and database schemas.
