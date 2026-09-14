# Recovery

Read this file completely after a definitive failure, stall, partial result,
check failure, or unusable diff, and before any resume, re-delegation, or
local fallback. Read it at most once per user task and never reload it between
waves.

## Diagnose once

Use `sail_collect` with `task_index` and `include_request=false` to inspect the
affected task. Do not poll, duplicate, or recover work that is still
progressing. Inspect status, `stop_reason`, summary, partial patch, checkpoint
state, check evidence, and cumulative usage.

A fanout with `status="partial"` can contain valid completed siblings. Integrate
those independently and recover only unfinished entries. Keep every fallback
inside the failed leaf's original ownership.

Treat check declarations separately from worker failures:

- `gate_suspect` means a post-work check failure may come from the invocation
  rather than the patch. The patch and checkpoint remain available. Inspect
  `failed_details` and the worker's diagnosis, then verify the invocation
  before continuing. Worker diagnosis is advisory and cannot replace the
  original gate.
- `no_changes` means a writable task produced no patch. Passing existing tests
  cannot prove the behavior was added; inspect the baseline before retrying.
- `scope_violation` preserves edits outside ownership for inspection. Remove
  those edits or resolve the dependency before applying the patch.
- A turn-ceiling result includes `required_checks` verdicts for the partial
  tree. Use that evidence to decide whether to continue.

## Choose one bounded continuation

If `resume_available=true` and the checkpoint contains useful work, call
`sail_resume` on that task instead of starting a fresh delegation. Each
checkpoint lasts 24 hours; a newly saved checkpoint refreshes that window.

A resume reruns the original setup by default. If partial edits make it
invalid, pass `setup_commands=[]` to skip setup or up to three replacement
commands. The override is one-shot. If resumed setup fails (`setup_failed`),
no turns were spent; pass the corrected `setup_commands` again and repeat the
same continuation.

Map `stop_reason` to one continuation:

- `inference_interrupted` (the connection to Sail was lost mid-turn) takes
  one `mode="continue"` resume, normally with no instruction: the worker
  replays the interrupted request with its saved idempotency key and
  retrieves the same generation without billing it again. Any instruction
  you pass is delivered after that replay. If that resume is itself
  interrupted before the replay lands, its direction is not carried in the
  new checkpoint: pass it again on the next resume. This is retrieval, not a
  repair attempt, so it does not count toward the two-attempt limit. The
  exception
  is a result whose `detail` says the in-flight request was keyless: there
  is nothing to retrieve, the resume starts a fresh turn that may bill that
  generation again, and it counts as a normal continuation.
- `insufficient_progress` (closed at the 24-turn gate) or `stalled` with a
  usable checkpoint may take one `mode="continue"` resume with the default
  24-turn budget. The worker was not progressing on its own, so the
  instruction must name the concrete next step: a file to edit, a check to
  run, or a design decision.
- `max_turns` (a hard-ceiling exit) is a healthy worker that ran out of
  room, not a broken one. Read its final report. If it says substantive work
  remains (files still to change, a build still to fix), use
  `mode="continue"` with the default 24-turn budget and an instruction naming
  the next concrete step. Repeat while each attempt shows evidence: new edits
  plus an attempted declared check. When the report says the work is done
  except for one named repair, or the worker claimed completion but returned
  `checks_failed`, `scope_violation`, or `no_changes`, use `mode="finalize"`
  with one instruction naming that repair. Finalize is repair, verify, and
  report only, and is capped at twelve turns; never use it to finish a
  refactor.
- `worker_error` (the resumed attempt died outside the worker's own
  recovery, for example an inference outage that outlasted its retries)
  keeps the checkpoint it started from. Resume once the cause is addressed;
  it does not count toward the attempt limit.
- Required checks are immutable on resume; `sail_resume` accepts none. When
  `gate_suspect` shows the check itself is wrong, re-delegate the leaf with
  corrected checks instead of resuming.

Stop after two consecutive attempts without evidence, meaning no new edits
or no attempted declared check. Apply any useful partial patch and make one
bounded local repair, or re-delegate the narrow leaf only when that is clearly
better. Tell the user what failed, what fell back, and why. Never retry
indefinitely or silently take over the whole task.

## Preserve partial value

Workers target a 24-turn primary budget. A writable attempt needs actual edits
and a worker-run declared check to overflow beyond turn 24; otherwise it
closes as `insufficient_progress`. An attempt can overflow to 128 turns, a
hard per-attempt ceiling with a finish-only checkpoint at turn 106. A lower
`max_turns` lowers the hard ceiling. Every ceiling exit gets a tools-withdrawn
final-report turn, so never resume merely for a summary.

If `omitted_files` is present, the partial patch excludes oversized new files
and has no resumable checkpoint. Repair only what is required. If compact
output says `omitted_files_truncated`, collect the indexed result for the
full list.

If `error` and `diff_error` accompany a summary, retain the paid analysis and
usage, but treat the patch as unavailable. Do not claim worker authorship for
work the host reconstructed.

Never apply or present `status="incomplete"` as finished. Local verification
still decides whether any recovered patch lands. Once recovery ends, report
the final cumulative delegation usage exactly once.
