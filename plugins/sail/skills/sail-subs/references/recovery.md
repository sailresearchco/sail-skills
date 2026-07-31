# Recovery

Read this file completely after a definitive failure, stall, incomplete or
partial result, check failure, unusable or empty diff, or before any resume,
re-delegation, or local fallback.
Read it at most once per user task and never reload it between waves.

## Diagnose once

Use `sail_collect` with `task_index` and `include_request=false` to inspect the
affected task. Distinguish an active task from a definitive failure. Do not
poll, start speculative duplicates, or recover work that is still progressing.
Inspect status, `stop_reason`, summary, partial patch, checkpoint state,
required-check evidence, and cumulative input, cached-input, and output usage.

A fanout with `status="partial"` can contain valid completed siblings. Integrate
those independently and recover only unfinished entries. Keep every fallback
inside the failed leaf's original ownership.

Treat check declarations separately from worker failures:

- `gate_suspect` means a post-work check failure may come from the invocation
  rather than the patch. The patch and checkpoint remain available. Inspect
  `failed_details` and the worker's diagnosis, then verify the invocation before
  resuming or re-delegating. Worker diagnosis is advisory and cannot replace
  the original gate.
- A genuine `checks_failed` result may be resumed only when its checkpoint
  contains useful work and one bounded repair is clear.
- A turn-ceiling result includes `required_checks` verdicts for the partial
  tree. Use that evidence when deciding whether continuation is worthwhile.

## Choose one bounded continuation

If `resume_available=true` and the checkpoint contains useful work, call
`sail_resume` deliberately on that task instead of starting a fresh
delegation. Resume preserves its conversation and partial edits. Each
checkpoint lasts 24 hours; a newly saved checkpoint refreshes that window.
The latest resumed result reports cumulative usage.

A resume reruns the original setup by default. If partial edits make it
invalid, pass `setup_commands=[]` to skip setup or up to three replacement
commands. The override applies only to that resume. If resumed setup fails,
the previous summary, partial patch, cumulative usage, and checkpoint remain.

A first resume may continue substantive work with the default turn budget.
After a turn-ceiling exit or `checks_failed`, use `mode="finalize"` with one
instruction naming the single repair. Finalize is repair, verify, and report
only, and is capped at eight turns. Original required checks still gate
completion.

Stop after two failed attempts. Apply any useful partial patch and make one
bounded local repair, or re-delegate the narrowly failed leaf only when that is
clearly better. Tell the user what failed, what fell back, and why. Never retry
indefinitely or broaden recovery into silent whole-task ownership.

## Preserve partial value

Workers target a 24-turn primary budget. A normal attempt can overflow to 48
turns, which is a hard per-attempt ceiling. Cohesive work can explicitly use a
hard 64-turn ceiling and receives a finish-only checkpoint at turn 53. A lower
`max_turns` lowers the hard ceiling.
Every ceiling exit receives a tools-withdrawn final-report turn, so a resume is
not needed merely to obtain a summary.

If `omitted_files` is present, the partial patch excludes oversized new files
and has no resumable checkpoint. Inspect the names and repair only required
missing implementation. If compact output says
`omitted_files_truncated`, collect the indexed result for the full list.

If `error` and `diff_error` accompany a summary, retain the paid analysis and
usage, but treat the patch as unavailable. Use the summary as context for one
bounded local repair or re-delegation. Do not claim worker authorship for work
the host reconstructed.

Never apply or present `status="incomplete"` as finished. Local verification
still decides whether any recovered patch lands. Once recovery ends, include
the final cumulative delegation usage exactly once in the user-facing total.
