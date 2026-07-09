---
name: sail-fanout-policy
description: Use to delegate or offload heavy coding and analysis work to GLM workers on Sail via the sail_delegate and sail_fanout MCP tools — when to hand a subtask to a Sail worker vs. do it yourself, how to fan out independent subtasks in parallel, and how to review and apply the diffs workers return. Applies whenever the sail-delegate MCP server's tools are available. For building or instrumenting a Sail Voyage use sail-voyage; for Sail model-call attribution use sail-inference-with-voyage.
---

# Delegating work to Sail workers

When the `sail_delegate` and `sail_fanout` tools are available, you can hand
self-contained subtasks to GLM workers running on Sail. Each worker operates
in an **isolated copy** of the project (a throwaway git worktree seeded with
the current working state — uncommitted changes included) and returns a
summary plus a **unified diff**. Workers never touch the live tree; you
review and apply their diffs.

This keeps your own conversation on the user's Claude plan while the heavy
token spend happens on the user's Sail account — the two credentials never
mix.

## When to delegate

Delegate work that is **self-contained and heavy**:

- Implementing a well-specified change scoped to known files or a subsystem.
- Large-scale reading: summarize/audit many files, trace a call graph,
  inventory usages before a refactor (`write=false`).
- Independent parallel subtasks — N similar migrations, per-module analyses,
  generating tests for several files at once (`sail_fanout`).
- Draft generation the user will iterate on anyway.

Keep for yourself:

- Final synthesis, judgment calls, and anything needing the conversation's
  full context (workers only know what you pass them).
- Small edits you can make faster than a worker round-trip.
- Work depending on tools only you have (browser, MCP servers, user dialog).

Delegations run for **minutes, not seconds** — they are background workers.
Prefer one `sail_fanout` call over sequential `sail_delegate` calls when
subtasks are independent.

## How to delegate well

1. **Write the task like a good ticket.** The worker cannot ask questions.
   State the goal, the acceptance criteria, and any conventions that matter.
2. **Ground it.** Pass `paths` for the files it should start from, and
   `context` for anything it can't discover in the checkout (decisions from
   the conversation, error messages, API quirks).
3. **Pick the mode.** `write=true` (default) lets the worker edit and run
   builds/tests in its sandbox and returns a diff. `write=false` is
   read-only analysis — cheaper and safer for pure research.
4. **Pick the completion window.** `priority` (default) for interactive
   work; `standard` for cost-optimized batches you are happy to wait a few
   minutes per turn on. `flex` is not available here — it is a best-effort
   batch tier with no targeted response time, and a delegation is polled
   synchronously to completion. See the Sail docs for pricing per window.
5. **Fan out independent tasks only.** Each `sail_fanout` task gets its own
   sandbox copy; workers cannot see each other's edits. If task B needs task
   A's changes, run them sequentially instead.

## Reviewing results

- **Read the diff before applying it.** Apply with `git apply` (or your edit
  tools) once satisfied; the summary states how the worker verified its work
  and what to double-check.
- A `diff` starting with `base64:` means the patch contains non-UTF-8 bytes:
  strip the prefix, base64-decode to a file, then `git apply` that file.
- Fanout results are per-task: some entries may carry an `error` while
  others succeeded. Handle partial success — re-delegate or finish failed
  tasks yourself.
- If a diff conflicts with edits you made while the worker ran, prefer your
  tree and re-delegate the remainder with updated context.
- `voyage_url` links the delegation's trace in the Sail dashboard for
  inspecting what the worker actually did.

## Requirements and limits

- The project must be a git repository with at least one commit (sandboxes
  are git worktrees).
- Workers authenticate with the user's `SAIL_API_KEY` (or a `sail auth
  login` credential). No Anthropic credential is ever sent to Sail.
- A delegation is one worker on one checkout — it cannot spawn sub-workers.
  With `write=true`, a delegated `run` executes untrusted repository code
  (builds, tests) with your OS access and network. The environment is
  scrubbed of inherited credentials and HOME is pointed at the sandbox, but
  that is not a filesystem boundary: such code can still recover your real
  home and read on-disk secrets — including the Sail key `sail auth login`
  stores under `~/.sail`, plus `~/.aws`, `~/.ssh` — and a command that
  daemonizes itself can outlive the delegation. Treat repository content as
  the trust boundary: prefer `write=false` for repositories you don't fully
  trust, and treat the containerized Sailbox executor as the real isolation
  boundary.

## Troubleshooting (relay these to the user)

- **A tool call returns an authentication error** ("No Sail API key is
  available…"): the server has no key yet. Tell the user to run `sail auth
  login` in a terminal, then simply **retry the tool — no restart needed**
  (the server re-reads the credential on every call). This is the
  desktop-safe path: a Dock-launched Claude Code app never sees a shell's
  exported `SAIL_API_KEY`. Need the CLI first? `curl -fsSL
  https://cli.sailresearch.com/install.sh | sh`. The alternative is `export
  SAIL_API_KEY=sk_...` and restarting Claude Code from that same shell.
- **`sail_delegate` / `sail_fanout` are missing entirely**: the
  `sail-delegate` MCP server failed to launch — most often because `uv` is
  not installed (the server runs via `uvx`). Tell the user to install it
  (`curl -LsSf https://astral.sh/uv/install.sh | sh`), reconnect the server
  from the `/mcp` menu, and inspect it with `claude mcp get sail-delegate`.
- **"not inside a git repository"**: delegation seeds a git worktree, so the
  project must be a git repo with at least one commit.
- Full guide: <https://docs.sailresearch.com/claude-code-delegation>.
