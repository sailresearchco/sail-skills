# Recovery

Read this file completely after failure, stalled or partial work, or concrete
review findings, including on completed patches, before resume or local
fallback. Read it once per task; never reload it between waves.

## Diagnose once

Use indexed `sail_collect` with `include_request=false`; omit known diffs.
Inspect status, `stop_reason`, checkpoint, check evidence, and usage before
worker claims. Read bounded diagnostics, not checkpoint conversations.
Do not recover running work. A fanout with
`status="partial"` can contain completed siblings; recover only affected tasks.

`gate_suspect` is a hint, not a diagnosis. Worker explanations cannot replace
the original gate. Inspect failed commands, termination reasons, and bounded
output in indexed results or `diagnostics_path`. Compiler exit 2 can mean real
code errors. Timeouts, signals, and missing executables route to infrastructure
diagnosis; `infrastructure_failure` does not establish the root cause or OOM.

`no_changes` requires checking whether the baseline already satisfies the task.
`scope_violation` requires repairing ownership before integration. Ceiling exits
also carry harness checks against the partial tree.

## Bounded repair

After claimed completion, failed declared checks receive at most two automatic
repairs sharing the original remaining turn allowance, with the usual progress
checks and no separate per-repair turn cap. Baseline, model, ownership,
conversation, and checks stay fixed.
`repair.attempts` persists across explicit resumes; these do not replenish it.
Progress stops do not automatically retry. Inspect `outcome` and `repair` before
requesting more work.

Default to review → concrete findings → worker repair → verify revised patch.
With useful work and `resume_available=true`, use `sail_resume`. Each checkpoint
lasts 24 hours; a new checkpoint refreshes it. Completed writable patches also
retain checkpoints. Pass the collected `patch_revision` as
`expected_patch_revision`, and findings plus requested regression coverage in
`instruction`; both are required for completed patches.

Omit `additional_turns`: continue defaults to a hard 128-turn allowance per
attempt. More turns never establish completion. Choose a mode:

- `insufficient_progress` or `stalled`: diagnose the missing evidence; use
  `mode="continue"` with a file, exact check, or resolved prerequisite. At the
  24-turn boundary, overflow requires edits and an attempted declared check.
  For persistence tasks, run the smallest real-DB check early against an
  accessible disposable database.
- `max_turns`: inspect remaining work and recorded progress. Continue substantive
  work only with a concrete next step; use `mode="finalize"` for narrow repairs.
  Finalize is repair, verify, report only, capped at twelve turns. Neither
  mode changes required checks or ownership.
- `inference_interrupted`: resume to retrieve the saved keyed generation.
  This retrieval is not repair. If interruption recurs, repeat any undelivered
  instruction. A keyless request cannot be retrieved and may bill again.
- `worker_error`: address the cause before resuming its preserved checkpoint.
- `setup_failed`: diagnose output before retrying. Resume reruns original setup;
  `setup_commands=[]` skips it, and up to three replacements override it once.
  Failed setup spends no model turns; repeat corrected overrides when retrying.
- A broken declared check requires a new delegation with corrected checks.
  Cancelled work is terminal; never resume it.

Healthy incomplete workers keep implementation ownership. Repeat directed
resumes while substantive edits and worker-attempted exact checks (if declared)
show progress
on remaining work; activity or harness checks alone do not prove health.
Stop after two consecutive attempts without evidence: new edits plus an exact
worker check attempt (if declared). Surface blockers or exhausted recovery. Small
local fixes remain allowed; explain substantial host takeover, not extra approval.

## Revisions and partial value

`diff_path` names an immutable full replacement patch from the original
baseline; `supersedes_revision` names its predecessor. Never apply both
revisions cumulatively. After application or overlapping host edits, merge in
a separate checkout against the current tree; preserve host edits. Resumes
cannot incorporate later host changes. If those are prerequisites, re-delegate
from the integrated baseline.

`omitted_files` or `diff_error` means the patch is incomplete or unavailable;
no safe checkpoint exists. Preserve useful analysis without claiming worker
authorship for host reconstruction. Never present incomplete work as finished.
Verify the integrated tree. Report final cumulative tokens and searches once,
including failed repairs; the harness does not measure host effort or savings.
