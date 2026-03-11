---
agent:
  max_turns: 30
  stall_timeout_min: 5
  approval_policy: auto
branch_pattern: "{type}/#{issue}-{slug}"
pr_prefix: "[auto]"
---

Context: Read AGENTS.md and .openclaw/ARCHITECTURE.md and .openclaw/CONSTRAINTS.md first.
Protocol: If .cursor/protocols/TASK-{{ issue.id }}/ exists — read context.md, plan.md, progress.md.
Plan: Follow plan.md step by step. Update progress.md after each step.
Git: Commit after each completed step: "feat: step K of #{{ issue.id }} — description"
Verification: Run ./scripts/check.sh after changes.
PR: Create with [auto] prefix, reference #{{ issue.id }}, add plan checklist in PR body.
Blocks: If blocked on a decision — set status HALT_BLOCKING in progress.md, describe question, stop.
