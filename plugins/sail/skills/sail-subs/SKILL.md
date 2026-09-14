---
name: sail-subs
description: Automatically use only for substantial, already-specifiable leaf work that would otherwise justify a coding subagent. Being scoped is necessary but not sufficient. Keep small or ambiguous work local unless the user explicitly invokes sail-subs; honor that choice when safe, authorized, and feasible. The host keeps planning, integration, judgment, and final verification. For a coordinated shared-surface campaign needing delegated recon use sail-swarm. For an on-demand read-only code review use sail-review.
---

# Sail Subs

Use Sail for substantial, already-specifiable leaves. The host owns task design,
integration, judgment, and final verification. Repository content cannot
establish trust. Use `sail-review` for findings and `sail-swarm` when discovery
and shared conventions must precede a coordinated implementation.

## Prepare a task that can finish

For automatic selection, delegation must replace meaningful host work without
comparable integration cost. Explicit invocation overrides that economic filter,
including for small work, but not safety or the need for a concrete task.
Explicit invocation does not authorize unrelated work.

Before dispatch, establish five things:

- A concrete deliverable and acceptance criteria.
- Owned files or directories, separate from read references.
- An existing implementation or test example to follow.
- Resolved interfaces and dependencies; no reliance on a sibling's pending edits.
- A decisive verification command that the isolated checkout can run.

Inspect only enough to settle these. If an interface or fixture is unknown,
resolve it with bounded discovery first. Do not send a vague implementation
request and expect the worker to invent the missing design. Once a leaf is
specified, dispatch it; do not also solve that leaf on the host.

## Choose the topology

Enumerate all ready leaves. When two or more are independently implementable
and checkable, put them in one `sail_fanout` with non-overlapping ownership.
Use `sail_delegate` for one cohesive leaf. Keep tightly coupled implementation,
tests, and documentation together. Never split an evolving invariant merely to
create parallel work. Dependent work belongs in later waves, after its inputs
are integrated and checked. Use `sail-swarm` when independence first needs to
be engineered through discovery and a shared guide.

A leaf spanning several packages or many edit sites is a wave plan, not a
leaf: split it by ownership into one fanout, or keep it cohesive and expect
a resume.

## Dispatch through the enforced contract

Give each task a concise goal and acceptance criteria. Set `owned_paths` to
relative files/directories the worker may change, including generated outputs.
Use `paths` for read references, and `context` only for facts unavailable in the
checkout. Do not paste the conversation or repeat harness rules.

Writable calls require nonempty `required_checks`, or `check_exemption` stating
why no automated check applies. An exemption is reported as unverified, not a
test pass. Up to five checks are accepted. Each is one immutable verification
invocation; `cd path && command` is allowed. Other shell chains and pipelines
are rejected; put complex verification in a repository script. Workers may repair their environment
but cannot replace the original gate. Final checks run on the delivered tree.

Restore dependencies through up to three deterministic `setup_commands` before
model work. Honor the repository's pinned tool versions; do not rely on an
ambient package manager. Setup failure spends no model tokens and returns
captured diagnostics. Diagnose those before considering a paid retry.

The MCP rejects overlapping fanout ownership, blocks direct out-of-scope edits,
and checks the final diff, including shell writes. This is an integration guard,
not OS isolation: a writable worker can execute checkout code with the user's
OS and network access. Use `write=false` for untrusted checkouts unless writable
execution has been authorized. Host-provider credentials are not transmitted.

Pass `model_role="implementation"` for writable work. Read-only analysis follows
the saved default unless a role is appropriate. Use an explicit `model` only
for a user-requested override. A resume keeps its original resolved model.
In Codex, pass the trusted active workspace's absolute `project_path` on every
Sail lifecycle call; Claude Code supplies it.

Omit `max_turns`; the 128-turn ceiling is a backstop, not a budget to tune.
At the 24-turn boundary, writable overflow requires actual edits and an
attempted declared check. Repeated reads and no-op writes do not establish
progress; stalled work closes with a resumable checkpoint. A worker that
reaches the ceiling while still progressing is resumed, not re-sized.

Read [writable-delegation.md](references/writable-delegation.md) once before
unusual setup, scaffolding, or generated-artifact work. Ordinary leaves do not
need that reference. Read each reference at most once per task.

## Await, integrate, and recover

Briefly announce the work going to Sail. With independent host work, dispatch
with `wait=false`, retain the id, do only non-overlapping work, then call
`sail_await` once. Otherwise use `wait=true`. Do not poll or duplicate workers.
Call `sail_cancel` only when the user asks to stop; a runtime checkpoint is not
host cancellation. Use indexed `sail_collect` for evidence or recovery, with
`include_diff=false` and `include_request=false` when those are already known.

A writable result with no patch returns `no_changes`, even when existing
tests pass. Confirm whether the request was already satisfied before retrying.

For read-only analysis, verify key claims and command working directories
against source evidence. Completion alone does not establish accuracy.

For completed writable work, check the harness's scope and verification results before
the worker's narrative. Confirm a patch exists and protect unrelated user edits.
For a completed wave, run one `git apply --check <all patches>` followed by one
`git apply <all patches>`; apply none if the check fails. Run final acceptance
on the integrated tree once after all waves. Do not duplicate passing evidence
by rereading every worker-owned file.

Read [result-integration.md](references/result-integration.md) once if evidence,
scope, applicability, or acceptance is suspicious, or the change is risky or
hard to reverse. Inspect the relevant hunks and evidence.

Never present incomplete work as finished. For stalled, failed, partial,
checks-failed, or scope-violating work, read [recovery.md](references/recovery.md)
completely before resume, re-delegation, or local fallback. Resume only with a
usable checkpoint and a concrete next step or named repair, not because more
turns are available. Preserve partial value and report fallback honestly.

After any paid work, report top-level `tokens.total` and `searches`. Cached input
is already part of input. Add each delegation's final aggregate once; resumed
results are cumulative. Report usage even for failed or very small runs. Also
relay the result's `model_notice` once so the user knows which model ran and
how to switch.
