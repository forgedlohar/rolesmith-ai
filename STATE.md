# STATE

## Done
- Phase 0: Baseline (Tests run: 3 passed, 0 failures. No LICENSE found, created NOTICE).
- Phase 1: Restructure and rename (behaviour-preserving)
- Phase 2: uv + pyproject

## In Progress
- Phase 3: Secrets and configuration with .env

## Open Questions
- There is no upstream LICENSE file. Added NOTICE file, but licensing gap needs decision.

## Decisions
- Using variables in `src/rolesmith/branding.py` as source of truth for app name, pkg, cli, env prefix.
