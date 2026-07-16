---
name: sail-migrate
description: "Use to migrate or switch an existing app, agent, or background workflow to Sail by moving OpenAI Responses or Chat Completions, Anthropic Messages, raw HTTP, or framework configuration to the Sail API, and by moving sandbox execution from E2B, Modal, Daytona, Docker, or another third-party sandbox to Sailboxes, since a Sailbox is Sail's sandbox. Covers call-site inventory, model and completion-window selection, in-place edits that preserve existing behavior, an optional before/after comparison run, and moving a compatible agent harness into a Sailbox. Trigger on migrate/switch/port/move to Sail, replacing an OpenAI-compatible or Anthropic inference endpoint with Sail, or moving sandbox execution or an agent harness to Sail. For building or instrumenting a Voyage use sail-voyage; for attributing model calls inside a Voyage use sail-inference-with-voyage."
---

# Migrate to Sail

Use this skill to move an existing project to Sail. A migration has up to two
legs, and a project may need either or both:

1. **Inference**: move OpenAI Responses, Chat Completions, or Anthropic
   Messages calls to the Sail API.
2. **Sandboxed execution**: move E2B, Modal Sandbox, Daytona, Docker-based
   execution, or another third-party sandbox to a **Sailbox**. A Sailbox is
   Sail's sandbox: a full Linux VM for long-running agent work.

**Preserve existing functionality first.** Deliver the same app, running on
Sail, with the same behavior. Migrate in place on a branch by changing
configuration and call sites, not prompts, tools, or business logic.
Recommend moving a compatible background harness into a Sailbox only after
the in-place migration works. Offer that end-state; never force it or block
the baseline migration on it.

## Ground rules

- Treat live docs as the source of truth for models, pricing, completion
  windows, and API support. Consult these pages while working:
  - <https://docs.sailresearch.com/models>
  - <https://docs.sailresearch.com/pricing>
  - <https://docs.sailresearch.com/completion-windows>
  - <https://docs.sailresearch.com/support>
  - <https://docs.sailresearch.com/sailbox-sdk>
  - Full docs: <https://docs.sailresearch.com/llms-full.txt>
  - Docs MCP server: <https://docs.sailresearch.com/mcp>
- Work on a branch and record the pre-migration commit before editing. Never
  stash, reset, or overwrite unrelated uncommitted changes. If the tree is
  dirty, tell the user and let them decide how to proceed.
- Never hardcode an API key, paste a literal key into code, or ask the user to
  paste a key to you. Read `SAIL_API_KEY` from the environment. The user can
  create a key at <https://app.sailresearch.com/api-keys> and export it in
  their own shell.
- Ask when a model choice or latency requirement is ambiguous. If you cannot
  ask, make the best-supported choice and flag it in the final report.
- Get approval before paid external calls. Baseline, comparison, and smoke
  requests cost real money on someone's account.

## Step 1: Inventory every inference call site

Before editing, survey the project for:

- OpenAI or Anthropic SDK clients and compatible wrappers
- raw HTTP calls
- framework and provider configuration
- environment variables and configuration templates
- README and deployment documentation

Also inventory sandbox call sites that create sandboxes, execute commands,
transfer files, expose ports, or manage lifecycle. For each one, record the
provider, whether the environment is per-command or long-lived, the image or
dependencies it needs, and the state that must survive between commands.

For each call site, record the API shape (Responses, Chat Completions, or
Messages), provider, model, and features in use: streaming, tool calls,
structured outputs, images, response chaining, background execution, and
caching.

Check every feature against <https://docs.sailresearch.com/support>. Two gaps
commonly change code shape:

- `previous_response_id` and `conversation` are not supported. Send the full
  input on each request instead.
- `background: true` requests return immediately and cannot stream. Poll or
  use webhooks for long-running background work. Foreground streaming is
  supported.

Flag unsupported features in the final report.

## Step 2: Offer and record a baseline

Offer a before/after comparison using the protocol in
[references/comparison-run.md](references/comparison-run.md). If the user
accepts, record the current commit and run the existing workflow on one fixed,
representative input before editing. Save its functional output, wall time,
and reported token usage. This spends money on the old provider, so get
approval first. If the user declines or lacks the old credentials, skip the
live baseline and say so in the report.

## Step 3: Choose replacement models

For each model in use, pick the closest match from the live
[model catalog](https://docs.sailresearch.com/models). Compare capability
tags, context window, and what each model is known to do well. Research an
unfamiliar current model before choosing. If several Sail models are
plausible, ask the user. Otherwise choose the best fit and explain why.

## Step 4: Choose a completion window per call site

Completion windows are a per-call-site decision and the main Sail-specific
cost tradeoff. Read the live
[completion-window](https://docs.sailresearch.com/completion-windows) and
[pricing](https://docs.sailresearch.com/pricing) pages for current timing and
per-model availability. If they are unavailable, use these stable semantics:

- `asap`: a person is actively waiting for each response
- `priority`: a latency-sensitive agent loop
- `standard`: an autonomous agent or pipeline; the normal default for
  background workloads
- `flex`: best-effort batch, evaluation, or offline processing; use
  `background=True` with the Responses API

Set `metadata.completion_window` explicitly on every call site, including
those using the default. Confirm the selected window is available for the
chosen model. Ask if the workload's latency tolerance is unclear.

## Step 5: Migrate inference in place

At each call site, or at the shared client configuration:

```python
import os

from openai import OpenAI

client = OpenAI(
    base_url="https://api.sailresearch.com/v1",
    api_key=os.environ["SAIL_API_KEY"],
)

response = client.responses.create(
    model="<model chosen in step 3>",
    metadata={"completion_window": "standard"},
    input=...,  # unchanged
)
```

- Use `https://api.sailresearch.com/v1` as the base URL for OpenAI-compatible
  Responses and Chat Completions clients.
- For the Anthropic SDK, use the bare host `https://api.sailresearch.com`.
  The SDK appends `/v1/messages`, so a `/v1` base URL incorrectly resolves to
  `/v1/v1/messages`. Pass `SAIL_API_KEY` as `auth_token`, not `api_key`, so
  the SDK sends the supported bearer authorization header.
- Read `SAIL_API_KEY` from the environment.
- Set the model and `metadata.completion_window` selected in steps 3 and 4.
- Use `background=True` for `flex` and very long-running Responses requests.
  Poll the returned response ID. Background requests cannot stream.
- Keep the request shape already in use. Do not rewrite Chat Completions to
  Responses, or Responses to Chat Completions, as part of the migration.
- Update environment-variable names, `.env.example`, configuration templates,
  and README or deployment instructions.
- Do not change prompts, tools, or business logic.

For example, preserve an existing Messages request while changing only its
client configuration, model, and completion window:

```python
import os

from anthropic import Anthropic

client = Anthropic(
    base_url="https://api.sailresearch.com",
    auth_token=os.environ["SAIL_API_KEY"],
)

message = client.messages.create(
    model="<model chosen in step 3>",
    metadata={"completion_window": "standard"},
    max_tokens=...,
    messages=...,  # unchanged
)
```

## Step 6: Migrate sandbox execution to Sailboxes

Install the Sail SDK (`pip install sail`, `npm install @sailresearch/sdk`, or
`cargo add sail-rs`). It reads the same `SAIL_API_KEY` used for inference.
Each Sailbox belongs to an app, which is a named grouping. Resolve the app
once with `mint_if_missing`.

| Third-party sandbox concept | Sailbox equivalent |
| --- | --- |
| Create a sandbox | `sail.Sailbox.create(app=app, name=...)` |
| Run a command to completion | `sb.run("cmd", timeout=...)` and inspect `.stdout` and `.exit_code` |
| Stream output, stdin, or a PTY | `sb.exec("cmd", timeout=...)`, consume its streams, then call `.wait()` |
| Read or write files | `sb.fs.read`, `sb.fs.write`, `sb.fs.ls`, `sb.fs.mkdir`, `sb.fs.remove`, `sb.fs.exists` |
| Use custom dependencies | pass `image=` to `Sailbox.create` |
| Expose a service | pass `ingress_ports=[...]`, then call `sb.wait_for_listener(port)` |
| Pause, sleep, resume, or destroy | `sb.pause()`, `sb.sleep()`, `sb.resume()`, `sb.terminate()` |
| Snapshot, template, or fan out | `sb.checkpoint()`, `Sailbox.from_checkpoint(...)`, `sb.fork()` |
| Reconnect by ID | `sail.Sailbox.get(sailbox_id)` |

```python
import sail

app = sail.App.find(name="my-agent", mint_if_missing=True)
sb = sail.Sailbox.create(app=app, name="worker-1")

result = sb.run("python3 run_task.py", cwd="/workspace", timeout=600)
print(result.exit_code, result.stdout)

sb.terminate()
```

Preserve the old sandbox's semantics while adapting its lifecycle:

- Treat a Sailbox as long-lived task compute, not a per-command sandbox. If
  the old code created a sandbox for each command, create one Sailbox per
  task and run many commands in it. A fresh environment per task is fine when
  the old behavior relied on that isolation.
- Bake dependencies into a custom image instead of installing them with
  runtime commands on every Sailbox.
- Set an explicit timeout on every `run` or `exec`. Check `exit_code`, or pass
  `check=True`, because a nonzero exit does not raise by default.
- Pass secrets through the `env=` mapping on `run` or `exec`. Never
  interpolate them into shell strings, include them in images, or write them
  into committed files.
- If the old sandbox exposed a service, expose the port and wait for its
  listener before connecting. See
  <https://docs.sailresearch.com/sailboxes-networking>.

## Step 7: Recommend the harness-in-Sailbox end-state

For a self-contained, non-interactive background agent, recommend running the
controller or harness itself inside a Sailbox after the in-place migration
works. This gives the harness a durable environment that can sleep while idle,
resume later, and serve as the source of checkpoints or forks.

Do not recommend this move blindly for interactive servers or code coupled to
private infrastructure a Sailbox cannot reach. Verify reachability and respect
the user's choice. Follow
[references/harness-in-sailbox.md](references/harness-in-sailbox.md) when the
workload fits.

## Step 8: Verify

1. Run the project's tests.
2. With approval and a configured `SAIL_API_KEY`, make one real request
   through the migrated inference configuration. If the sandbox leg exists,
   run one real Sailbox command and clean up any Sailbox created by the smoke.
3. If no key is configured, walk the user through creating one and exporting
   it in their own shell. Do not ask them to paste it to you.
4. If the user opted into the comparison, run the migrated branch on the same
   fixed input as the step 2 baseline. Follow
   [references/comparison-run.md](references/comparison-run.md) when
   comparing functionality, latency, tokens, and approximate cost.
5. If the user moved the harness, run the same fixed input inside the Sailbox
   and confirm that only the controller's location changed.

## Step 9: Write the migration report

Finish with a short report containing:

- call sites changed, grouped by inference and sandbox legs
- model mapping and rationale
- completion window per call site and rationale
- a simple, approximate comparison of published per-million-token prices for
  the old and new models; do not present it as a bill forecast
- before/after outputs, latency, tokens, and cost if the comparison ran;
  explicitly qualify normal model nondeterminism and completion-window latency
- whether the harness-in-Sailbox end-state was offered, adopted, or unsuitable
- unsupported features, ambiguous choices, and untested paths
- exactly where to set `SAIL_API_KEY` locally and in the deployment system

Optionally wrap the migrated workflow in a Voyage to record each run as a
dashboard trace. See `sail-voyage`; do not add Voyage instrumentation as part
of the migration itself.

## Hard rules

- Do not change prompts, tools, or business logic while migrating.
- Do not hardcode, print, or request pasted API keys.
- Do not silently substitute a model or completion window when unsure.
- Do not put secrets in shell strings, images, or committed files.
- Do not stash, reset, or overwrite unrelated user changes.
- Do not create a duplicated source tree for comparison. The git history is
  the old version.
- Do not create a Sailbox per command.
- Do not add Voyage instrumentation beyond recommending `sail-voyage`.
