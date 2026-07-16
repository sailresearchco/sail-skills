# Before/After Comparison Run

Use this optional mode to run the pre-migration and post-migration code on the
same fixed input and report what changed. It provides strong evidence that the
migration preserved behavior and makes the latency and cost discussion
concrete.

The git history is the old version. Never create an `_old` module, parallel
files, or a duplicated source tree for comparison.

## Protocol

1. Before editing, record the pre-migration commit with `git rev-parse HEAD`.
   If the tree has unrelated uncommitted changes, tell the user and let them
   decide how to proceed. Never stash, reset, or overwrite their work.
2. With approval, run the old workflow once on a fixed, representative input.
   Capture its functional output, wall time, and reported token usage. This
   spends money on the old provider. If its credentials are unavailable or
   the user declines, skip the live baseline and use a static diff review.
3. On the migration branch, run the same input through Sail after getting
   approval for that paid call. Capture the same measurements.
4. Compare the runs in the migration report:
   - Judge functional equivalence by substance and output shape, not exact
     text. Model outputs can differ even when no migration occurred.
   - Qualify latency against the chosen completion window. A lower-cost window
     intentionally trades turnaround time for price.
   - Report tokens and approximate cost using each side's current published
     per-million-token prices.

## Lower-cost variants

- When provider configuration comes entirely from environment variables, use
  an environment-toggle comparison so the same working tree can call either
  provider without parallel source files.
- When cost is the constraint, offer a smaller fixed input. If the user still
  declines, skip the paid comparison and report that limitation.
