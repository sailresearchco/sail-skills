# Result integration

Read this file only when scope, ownership, check evidence, patch application,
or final acceptance is suspicious or fails, or when a change is risky, hard to
reverse, or overlaps user work. Read it at most once per user task and never
reload it between waves.

Confirm the result is complete and matches the delegated scope. Inspect only
the relevant hunks at `diff_path`, or request an inline patch for a small
result. Narrative claims are not evidence. Preserve unrelated user work and
resolve conflicts in favor of the live checkout.

Writable results include a machine-recorded `command_runs` ledger for setup,
worker, and harness-required commands. Each entry has an exit code and a
`stale` flag when the tree changed after that run, including changes made by a
formatter or generator. `commands_total` counts all commands,
`command_runs_truncated` marks a trimmed ledger, `edits_total` counts tree
changes, and `required_checks` summarizes the final gate. Trust this evidence
over the summary. A passing `git status` is not a test. A result without a
fresh passing check for its final state is unverified regardless of status.
Compact terminal evidence retains nested `failed_details` and `gate_suspect`,
the last command record, patch metadata, and aggregate usage. Collect the
indexed result only when that compact evidence is insufficient.

Fanout results retain per-task ownership. Inspect and apply each completed
patch only as deeply as the suspicious evidence requires. Default compact
results omit inline diffs; fetch an indexed task with
`include_request=false`, and set `include_diff=true` only when inline content
helps. Larger patches remain at their absolute paths.

If a diff begins with `base64:`, decode the remainder before applying it with
`git apply`. If the result is incomplete, partial, stale, missing required
files, or otherwise unusable, stop integration. The core recovery gate applies.

After resolution, return to the core wave-level batch apply and one final
acceptance suite. Preserve the top-level token aggregate for the required Sail
usage line; do not sum a resumed task's earlier attempt twice.
