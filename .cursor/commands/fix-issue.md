# /fix-issue N

1. `gh issue view N` — read full description and acceptance criteria
2. Read AGENTS.md, .openclaw/ARCHITECTURE.md, .openclaw/CONSTRAINTS.md
3. If .cursor/protocols/TASK-N/ exists — read context.md, plan.md, progress.md
4. Find relevant code with grep/search
5. Implement fix following the plan
6. `./scripts/check.sh` — verify no regressions
7. Update progress.md (mark steps done)
8. Commit: `fix: description (#N)`
9. Create PR: `[auto] fix: description (#N)`
