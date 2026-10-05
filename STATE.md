# STATE

## Done
- Phase 0: Baseline (Tests run: 3 passed, 0 failures. No LICENSE found, created NOTICE).
- Phase 1: Restructure and rename (behaviour-preserving)
- Phase 2: uv + pyproject
- Phase 3: Secrets and configuration with .env

## In Progress
- Phase 4: Makefile (self-documenting)

## Open Questions
- There is no upstream LICENSE file. Added NOTICE file, but licensing gap needs decision.

## Decisions
- Using variables in `src/rolesmith/branding.py` as source of truth for app name, pkg, cli, env prefix.
