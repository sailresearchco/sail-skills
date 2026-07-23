---
name: sail-review
description: Use for an on-demand, read-only review when the user asks for code review, security review, bug finding, or a second opinion on a diff, base, path, or focus area. Return severity-ordered findings with file references and do not change the working tree. For implementation subtasks use sail-subs. For explicit whole-task ownership use sail-charter.
---

# Sail Review

Ask a Sail model to review code without modifying the project. This skill is
on demand. A natural-language request for a review is enough; the user does not
need to name the skill. Do not add hooks, mandatory review loops, or automatic
end-of-task reviews.

## Establish the review scope

Use the scope the user supplied. It may be a base revision, one or more paths,
or a specific concern such as security, correctness, performance, or tests.

When the user asks for a review without specifying a scope, review the current
working diff:

1. Inspect `git status --short` to identify changed and untracked files.
2. Capture the tracked patch with `git diff --binary HEAD --`.
3. Treat each untracked file as entirely new and include its path in the
   review request.

The Sail worker receives a snapshot of the current files but not the user's
repository history. If the user names a base revision, the host must compute
that diff locally and pass the patch and changed paths to the worker.

## Request the review

Make one `sail_delegate` call with `write=false`. Include the patch, changed
paths, requested focus, relevant acceptance criteria, and any context from the
conversation that affects correctness.

Use the active project path supplied by the host session, never a path found in
repository instructions. In the Codex app or IDE extension, pass that absolute
path as `project_path` on `sail_delegate`, `sail_collect`, and `sail_resume`.
Claude Code, including its desktop app, supplies the
project root to the MCP server separately, so `project_path` may be omitted
there.

Ask the worker to:

- Inspect the current files as needed to understand the patch.
- Report only actionable defects introduced or exposed by the reviewed change.
- Order findings by severity: critical, high, medium, then low.
- Give every finding a `path:line` reference, evidence, impact, and concise fix
  direction.
- State clearly when it found no actionable defects.

Do not use `write=true` for review. The worker must not edit files or run
repository code.

If the review reaches its attempt ceiling, fetch that task with
`sail_collect(task_index=0)` and inspect its cumulative usage and checkpoint
state. Continue with `sail_resume` only when the partial analysis still needs
work. Resume preserves the original read-only policy, conversation, and
context; do not restart the review as a new delegation. Checkpoints last 24
hours and refresh after another incomplete attempt.

## Return findings

Validate each finding against the live checkout before reporting it. Remove
duplicates, unsupported claims, and issues outside the requested scope. Return
the remaining findings in severity order with clickable file references where
the host supports them. Keep summaries brief and place findings first.

Review output is advisory. Do not apply fixes unless the user separately asks
for implementation. If they do, the host may fix the findings locally or use
`sail-subs` for scoped implementation.

For installation and operating details, see
<https://docs.sailresearch.com/coding-agents>.
