# STATE.md

## Done
- Cloned `job-apply-mcp`
- Phase 1 & 2: Setup workspace, requirements, and venv
- Phase 3: Create `autopilot/` package (`settings.py`, `models.py`, `llm.py`, `profile_store.py`, `store.py`)
- Phase 4: Implement `jd.py`, `rating.py`, `tailor.py`, `render.py`
- Phase 5: Implement `llm_answers.py`, `pipeline.py`, `cli.py`, `__main__.py`
- Phase 6: Modify base files (`tools/profile.py`, `tools/apply.py`, `server.py`)

## In Progress
- Phase 7: Write tests in `tests/test_autopilot.py` and get them passing

## Decisions
- Work in phases and commit after each phase
- Isolate the new feature within the `autopilot` package

## Open Questions
- None so far
