# Sail Skills

Use Sail models from the coding agent you already work in. The Sail plugin can
delegate scoped coding work, run a coordinated multi-worker campaign, or
request a read-only review. Your coding agent keeps ownership of the task in
every case. It also includes skills for migrating applications to Sail and
using preemptible GPU compute.

The plugin uses standard `SKILL.md` folders and one `sail-delegate` MCP server.
The same skill payload and server launch command ship for Claude Code and local
Codex sessions. DeepSeek V4 Flash 0731 is the initial worker default. You can
save a different default and optional overrides for recon, implementation, and
review work with the model picker skill. These settings persist on the same
device and affect new delegations. An explicit model on one delegation still
wins for that call. When a selected model is unavailable for delegation, Sail
can fall back to GLM-5.3 and records the model that served.

The server exposes nine tools: `sail_delegate`, `sail_fanout`, `sail_await`,
`sail_collect`, `sail_resume`, `sail_cancel`, and three tools for reading,
setting, and resetting local model preferences. Workers aim to finish within
a 24-turn primary budget, with overflow capped at 48 turns per attempt. An
attempt that reaches its turn limit can save its conversation and partial patch
for 24 hours so the coding agent can continue with `sail_resume`. Cancellation
is terminal but preserves partial work captured during safe shutdown.
Writable calls can also declare `setup_commands`, which restore dependencies
inside the isolated project copy before the worker's first model turn, and
`required_checks`, which Sail runs after the worker finishes to gate
completion.

Installation, usage, and troubleshooting are covered in
[Sail for coding agents](https://docs.sailresearch.com/coding-agents).

## Included skills

| Skill | Use it when |
| --- | --- |
| `sail-subs` | Have Sail workers investigate code, explore approaches, and implement changes. |
| `sail-swarm` | You want one change made across a real multi-worker campaign, and the pieces still need discovering. The host shows you the plan first, then runs paid scouting and coordinates the workers. |
| `sail-review` | You want findings on a diff, worst first, with nothing changed. |
| `sail-pick-models` | Choose the persistent default and role overrides used by new Sail delegations. |
| `sail-update` | Update the installed Sail plugin from the current coding agent and verify its version. |
| `sail-migrate` | Migrate an application's inference or third-party sandbox execution to Sail while preserving behavior. |
| `sail-gpu-marketplace` | Allocate, connect to, and release a preemptible GPU VM, or recover checkpointed work after an interruption. |

The line to remember: several jobs is Subs; one sweeping job that needs
scouting first is Swarm.

## Install

### Claude Code

```text
/plugin marketplace add sailresearchco/sail-skills
/plugin install sail@sail
```

Skills load automatically when relevant. You can also invoke one directly,
such as `/sail:sail-subs` or `/sail:sail-review`. Direct invocation overrides
automatic economic routing, but not safety, authorization, or structural
feasibility.

### Codex

```sh
codex plugin marketplace add sailresearchco/sail-skills
codex plugin add sail@sail
```

The Codex package includes all seven skills and the `sail-delegate` MCP server.
The server works in local Codex app, CLI, and IDE sessions. Hosted Codex
sessions cannot run the bundled local stdio server. Codex automatically
approves delegation, fanout, waiting, collection, resume, and reading model
preferences. Cancellation and preference changes still ask because they stop
active work or change persistent local settings.

Invoke a skill directly with `$sail-subs`, `$sail-swarm`, or another skill
name. Direct invocation overrides automatic economic routing, but not safety,
authorization, or structural feasibility.

## Check progress and continue work

Every delegation has a durable `delegation_id`. Use `wait=true` when the host
has no independent work. Otherwise start with `wait=false`, do real
non-overlapping work, then call `sail_await` once. Reserve `sail_collect` for
inspection and recovery rather than timed polling.

A default `sail_collect` call returns compact task status. Fetch one task by
index for its summary, cumulative token usage, checkpoint state, and diff
metadata. Set `include_request=false` to omit the known request and context.
Non-empty patches have an absolute path, byte count, and SHA-256; selected
patches up to 32 KiB can also return inline.

Token usage separates `input`, `cached_input`, and `output`. Sail reuses one
prompt cache identifier across the original attempt and every resume. Results
and patches remain available for seven days, while each checkpoint expires
after 24 hours unless another incomplete attempt refreshes it.

For a selected incomplete task, the coding agent can continue without starting
over:

```text
sail_resume(
  delegation_id="<id>",
  task_index=0,
  instruction="Finish the remaining verification.",
  wait=true
)
```

## Authentication

Installing the plugin does not require a Sail API key. Authenticate before the
first delegation:

```sh
sail auth login
```

If you need the CLI first:

```sh
curl -fsSL https://cli.sailresearch.com/install.sh | sh
```

You can instead export `SAIL_API_KEY` before starting your coding agent. A
stored login is more reliable for desktop apps because they may not inherit
shell variables.

## Update

On version `0.3.0` or later, use `/sail:sail-update` in Claude Code or
`$sail-update` in Codex. The coding agent runs the client update commands and
verifies the installed version. Reload plugins or start a new session when it
finishes.

The delegation server checks the published plugin version at most once per day.
When an update exists, one tool result asks your coding agent to mention that
version after finishing the current task. A running server mentions each version
at most once and records delivered notices when possible. In another client,
use the same installation channel to update the Sail skills and tools. Failed
checks stay silent. Set `SAIL_PLUGIN_UPDATE_CHECK=0` before starting the server
to disable the check.

If the update skill is missing, follow the manual update instructions in
[Sail for coding agents](https://docs.sailresearch.com/coding-agents) once to
reach `0.3.0` or later.

## Contributing

This repository is a curated export from Sail's source tree. See
[CONTRIBUTING.md](./CONTRIBUTING.md) before proposing a change.

## License

[Apache-2.0](./LICENSE)
