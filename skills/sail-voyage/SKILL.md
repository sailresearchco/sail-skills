---
name: sail-voyage
description: Use to build or instrument a Sail Voyage — Sail's name for one background or long-running agent run, recorded as a trace of named agents, spans, and events. The entrypoint skill for any Voyage, covering series/version naming, the init→agent→span→event→complete loop, multi-agent structure, bounded secret-safe payloads, child-process attach, and terminal lifecycle, from a minimal smoke to a polished production series. Use this first. For the model-call attribution contract use sail-inference-with-voyage; for a Voyage that renders wrong in the dashboard use sail-voyage-debugging.
---

# Sail Voyage

Use this skill to instrument any background or long-running agent run on Sail
Voyages so the dashboard shows its trajectory. Sail provides the flight
recorder; it does not run the agent for you.

This is the entrypoint skill. Start here whether you are smoke-testing a one-off
run or shipping a polished, repeatable production workflow such as deep
research, code review, eval generation, support triage, migration analysis, or
scheduled monitoring. The same `init → agent → span → event → complete` loop
covers all of them; you scale detail up, not skills.

For two adjacent concerns, reach for a focused sibling skill:

- attributing Sail inference model calls to the active agent/span →
  [sail-inference-with-voyage](../sail-inference-with-voyage/SKILL.md)
- a Voyage that looks wrong in the dashboard →
  [sail-voyage-debugging](../sail-voyage-debugging/SKILL.md)

For the full multi-agent attribution model (slug vs name vs role, per-agent
pitfalls, SQL verification), see
[references/multi-agent.md](references/multi-agent.md). For a complete runnable
skeleton, see [references/minimal-example.md](references/minimal-example.md).

## The Voyages model

- A **Voyage** is one concrete run (one trace).
- A **series** is the recurring workflow, identified by the user-facing `name`.
- A **version** is a positive integer for meaningful workflow changes.
- The dashboard starts from `/voyages`, groups by series, and links each run to
  `/{env}/voyages/{voyage_id}`.
- `voyage_series_id` is internal. Do not ask users to provide it, log it, or
  build URLs around it.

If you have used an LLM/agent tracing tool, the vocabulary maps cleanly:

| Sail term       | Standard tracing equivalent                       |
| --------------- | ------------------------------------------------- |
| Voyage          | one trace / one run                               |
| series (`name`) | the recurring workflow / project grouping         |
| agent           | an agent span / participant (`name` + `role`)     |
| span            | a span / unit of work                             |
| event           | a structured point logged on the trace            |
| model call      | an LLM span (Sail inference, auto-attributed)     |
| Sailbox exec    | a tool/exec span (auto-attributed by Sail) |

## Quickstart: a minimal Voyage

The smallest useful Voyage: init exactly one Voyage at task entry, do work
inside an agent/span, and mark exactly one terminal state at exit.

```python
import sail

voyage = sail.voyage.init(
    name="repo-repair",
    version=1,
    metadata={"repo": "example-org/example-repo", "task": "eval"},
)
try:
    with voyage.agent("executor", name="Executor", role="executor"):
        with voyage.span("run task"):
            voyage.event("task.started", payload={"step": 1})
            # ... do work ...
    voyage.complete(message="task complete")
except Exception as exc:
    voyage.fail(error_type=exc.__class__.__name__, message=str(exc))
    raise
```

Use module-level `sail.voyage.*` helpers for the process-global current Voyage,
or keep the returned `voyage` object when multiple handles are present. If the
task controls a Sailbox, bind it: `sail.voyage.init(..., sailbox_id=sb.sailbox_id)`.

## Production shape

Every production Voyage should answer these in the dashboard:

1. What recurring workflow is this?
2. Which workflow version ran?
3. Which agent owned each important decision or side effect?
4. Which model calls and Sailbox execs happened under each span?
5. What did the run produce?
6. Did it complete, fail, or get cancelled?

Map those questions onto the SDK like this:

```python
import os
import sail

voyage = sail.voyage.init(
    name="deep-research",
    version=3,
    metadata={
        "topic": "public launch plan for Sail Voyages",
        "source": "blog-demo",
        "commit": os.environ.get("GITHUB_SHA"),
    },
)

with voyage.agent("planner", name="Planner", role="planner"):
    with voyage.span("scope research question"):
        voyage.event("research.scope.selected", payload={"question_count": 4})

with voyage.agent("researcher", name="Researcher", role="researcher"):
    with voyage.span("collect sources"):
        response = sail.inference.responses.create(
            model="zai-org/GLM-5",
            input="Collect a concise source map for the topic.",
            background=False,
            timeout=120,
        )
        voyage.event("research.sources.collected", payload={"response_id": response["id"]})

with voyage.agent("publisher", name="Publisher", role="publisher"):
    with voyage.span("write final artifact"):
        voyage.event(
            "artifact.report.ready",
            payload={
                "artifact_type": "html_report",
                "path_hint": "/tmp/voyage-output/report.html",
                "summary": "Draft report generated and ready for operator review.",
            },
        )

voyage.complete(message="deep research complete")
```

## Choose the series name

`name` is the stable user-facing series identity. It should describe the
workflow, not the input, run date, environment, Sailbox, branch, or Voyage id.

Good names: `deep-research`, `code-review`, `nightly-backend-eval`,
`support-triage`, `release-risk-scan`.

Poor names: `deep-research-2026-06-05`, `voy_v7f...`, `prod-run`,
`github-pr-2381`, `kavin-test-2`.

Put changing run context in `metadata`, not in `name`:

```python
voyage = sail.voyage.init(
    name="code-review",
    version=4,
    metadata={"repo": "example-org/example-repo", "pr_number": 42, "head_sha": "abc123"},
)
```

Names are not lowercased, slugified, or whitespace-normalized by the product
contract. `Code Review` and `code-review` are different series. Pick one
spelling and keep it stable.

## Choose the version

`version` is a workflow-definition dimension. Increment it when behavior
meaningfully changes:

- prompt or system instruction changes
- model/provider changes
- tool set changes
- Sailbox image or command harness changes
- agent topology changes
- validation rubric changes
- output format changes

Do not increment it for: a new PR, repo, issue, customer, topic, or dataset; a
date or schedule tick; a rerun of the same workflow; a new Sailbox id; a new
Voyage id; or a failed run you retry with the same code.

Skipped versions are valid; versions need not be contiguous because they may
align with an external workflow release system. If omitted, `version` defaults
to `1`. For public demos, set an explicit version so the dashboard tells readers
which iteration produced the run.

## Design agents for dashboard readability

Agents are customer-facing ownership labels. Use a small, stable set that
matches real responsibility boundaries.

| Agent name | Role             | Owns                                                        |
| ---------- | ---------------- | ----------------------------------------------------------- |
| Planner    | `planner`        | goal decomposition, acceptance criteria, execution plan     |
| Researcher | `researcher`     | source collection, browsing, retrieval, notes               |
| Analyst    | `analyst`        | evidence comparison, scoring, synthesis                     |
| Executor   | `executor`       | Sailbox commands, tests, generated files, tool side effects |
| Reviewer   | `reviewer`       | critique, validation, risk review                           |
| Publisher  | `publisher`      | final report, blog draft, handoff summary                   |
| GitHub     | `source_control` | clone, fetch, PR/file metadata, posting comments            |

Rules:

- The table is a menu, not a checklist. Instantiate only the agents your task
  genuinely needs — two or three is common; use more only when each one owns a
  real responsibility boundary.
- Keep the same agent names and roles across runs of one series.
- Put each model call or exec under the agent that caused it.
- Do not use `Agent 1`, `Worker`, or `Assistant` unless that is genuinely the
  product vocabulary.
- Do not create a new agent for every span. Agents are participants; spans are
  steps.
- Keep terminal lifecycle at the top level after all agent blocks exit.

When one Voyage involves multiple cooperating agents (e.g. a Reviewer that reads
code and a TestRunner that runs tests in a shared Sailbox), each agent gets its
own spans, events, model calls, and exec rows but they all belong to one Voyage.
For the `slug` / `name` / `role` distinction, the full multi-agent example,
common mis-attribution pitfalls, and the verification SQL, see
[references/multi-agent.md](references/multi-agent.md).

## Design spans for causality

A span is one logical unit of work — specific enough to explain what happened,
not so granular that the trace becomes noise.

Good span names: `scope research question`, `collect primary sources`,
`run repository tests`, `synthesize findings`, `write report`.

Poor span names: `step 1`, `do thing`, `loop`, `llm call`, `processing`.

Use nested spans sparingly. Prefer a flat sequence inside each agent unless
there is a real parent/child relationship.

## Emit events that explain state changes

Events should be bounded, structured, and useful to a reader. Emit them for
phase starts/completions, tool outcomes, validation decisions, and final output
handoff.

```python
voyage.event(
    "research.sources.collected",
    payload={"source_count": 12, "primary_source_count": 5, "query_count": 4},
)
voyage.event(
    "validation.completed",
    payload={"checks_passed": 7, "checks_failed": 0, "risk": "low"},
)
```

Do not emit full model transcripts, full stdout/stderr, raw web pages,
credential-bearing URLs, or any secret material. If output is large, store a
short summary, count, hash, or path hint. Path hints are evidence only; they are
not durable artifact links until first-class Voyage artifacts exist.

## Attribute Sail inference

Calls through `sail.inference.*` inherit the active Voyage, agent, and span, so
the dashboard shows scoped model rows under the right owner.

```python
with voyage.agent("analyst", name="Analyst", role="analyst"):
    with voyage.span("compare evidence"):
        response = sail.inference.responses.create(
            model="zai-org/GLM-5",
            input="Compare the collected claims and identify contradictions.",
            background=False,
            timeout=120,
        )
        voyage.event("analysis.completed", payload={"response_id": response["id"]})
```

Prefer `background=False` for deterministic demos and smokes. For the header
contract, background-vs-synchronous behavior, raw-OpenAI-client wrapping, and the
immutable-`response_id` rule, see
[sail-inference-with-voyage](../sail-inference-with-voyage/SKILL.md).

## Attribute Sailbox execs

Run Sailbox commands inside an active agent and span. Sail records
`voyage_id`, `span_id`, and `agent_id` on the native exec evidence
automatically.

```python
def redact_tail(text, limit=2000):
    text = text or ""
    # Replace with your production token/secret redaction policy.
    return text[-limit:]


with voyage.agent("executor", name="Executor", role="executor"):
    with voyage.span("run validation command"):
        req = sb.exec("cd /tmp/work && pytest -q", timeout=600)
        result = req.wait()
        voyage.event(
            "validation.command.completed",
            payload={
                "exec_request_id": req.exec_request_id,
                "returncode": result.returncode,
                "stdout_tail": redact_tail(result.stdout),
                "stderr_tail": redact_tail(result.stderr),
            },
        )
        if result.returncode != 0:
            raise RuntimeError("validation command failed")
```

Rules: always set a non-zero `timeout`; record `exec_request_id` so manual
events dedupe against native rows; keep stdout/stderr tails bounded and
redacted; never put API keys, GitHub tokens, or bearer tokens in shell strings.
Never work around a private repo by embedding a token in a shell string, image
env, or guest file. Sail supports scoped per-exec credential injection for
private repos, but it requires Sail-provisioned org setup and is not part of
the public v1 package — contact Sail if you need it.

Do not rely on Sailbox APIs to auto-create Voyages, and do not pass the API key
into Sailbox commands to make guest code attach by default.

For real Python work in the guest (not just shell), pass a `@sail.function` to
`sb.exec(fn, *args)` — it runs in the Sailbox and returns the value, and still
produces an attributed exec row. Keep the function self-contained (imports
inside) so it ships cleanly to the guest. If a guest function imports
third-party packages, bake them into the image —
`sail.Image.debian_arm64.pip_install("matplotlib").build()` — rather than
installing them with a runtime exec, which is slower and adds a failure mode. To retrieve an artifact the guest
produced (a chart, a report file), read it back on the controller with
`data = sb.read(path)`, then record a bounded `artifact.*` event (type, path
hint, bytes, sha256) — not the bytes themselves. See
[references/minimal-example.md](references/minimal-example.md) for a complete
runnable skeleton that exercises every path above.

## Child and multi-process runs

Keep one Voyage per logical task. A subprocess that does not read
`SAIL_VOYAGE_ID` creates its own orphaned Voyage. Use child attach only when the
child already receives credentials through a secure channel:

```python
# parent
import os, subprocess, sys
env = dict(os.environ)
env["SAIL_VOYAGE_ID"] = sail.voyage.id()
subprocess.run([sys.executable, "child.py"], env=env, check=True)

# child
import sail
sail.voyage.init()  # attaches to SAIL_VOYAGE_ID when SAIL_API_KEY is present
```

`SAIL_VOYAGE_ID` is correlation only; `SAIL_API_KEY` still authorizes event
delivery. Do not use this pattern to smuggle credentials into Sailbox guest
commands.

## Report outputs honestly

Until first-class Voyage artifacts ship, output events must be explicit about
what they are:

```python
voyage.event(
    "artifact.report.ready",
    payload={
        "artifact_type": "markdown_report",
        "path_hint": "/tmp/voyage-output/report.md",
        "bytes": 18432,
        "sha256": "3f2b...",
        "summary": "Report drafted with executive summary, evidence table, and appendix.",
    },
)
```

A path hint helps an operator inspect the live Sailbox or copied output; it is
not a durable download URL. Retention, preview, download, and redaction belong
to future artifact work.

## Payload hygiene and secret safety

Keep payloads small, structured, and secret-free.

- Redact API keys, bearer tokens, credentials, cookies, and private URLs before
  recording stdout/stderr or tool outputs.
- Cap stdout/stderr snippets; prefer the last 1–4 KiB over full logs.
- Do not put secrets in `name`, `message`, `payload`, `metadata`, stdout,
  stderr, span names, or final printed JSON.
- Record identifiers — `exec_request_id`, `response_id`, `sailbox_id`, return
  code, duration — and bounded/redacted tails.

Hard prohibitions:

- Do not put `SAIL_API_KEY` or any secret into `Sailbox.exec()` shell strings.
- Do not bake API keys into image env, Dockerfiles, setup scripts, or payloads.
- Do not print API keys to stdout/stderr for Voyage collection.
- Do not log credential file contents for debugging.
- Do not add an agent framework, orchestration layer, memory graph, swarm, or
  Sailbox auto-binding when the task only needs Voyage telemetry.
- Do not use streaming inference wrappers; use a raw client with
  `sail.voyage.headers()` if streaming is required.

## Terminal lifecycle

Always mark exactly one terminal state at top level, after all agents, model
calls, execs, and output events have finished. `complete()` and `fail()` flush
synchronously and may raise delivery errors.

```python
voyage = sail.voyage.init("deep-research", version=3, metadata={"source": "blog-demo"})
try:
    phase = "run_workflow"
    run_workflow(voyage)
    phase = "complete"
    voyage.complete(message="deep research complete", payload={"validation": "passed"})
except Exception as exc:
    voyage.fail(error_type=exc.__class__.__name__, message=str(exc), payload={"phase": phase})
    raise
```

Call `voyage.flush()` before external assertions, SQL smoke checks, or process
handoffs that depend on recently emitted events. Terminal status is
first-terminal-wins; do not call `complete()` from inside a nested agent context
or while background threads or model calls may still emit.

## Verify the Voyage

At minimum, print the handoff and confirm terminal state:

```python
print(sail.voyage.id())
print(sail.voyage.dashboard_url())
```

Then confirm in the dashboard:

- `/voyages` shows the expected series name and version, with exactly one
  `voyage.started`.
- Agents show meaningful names, not generic placeholders.
- Spans, events, and native Sailbox exec rows appear under the right agents in
  Execution Trace.
- Native model calls are scoped — `Scoped > 0`, `Unscoped = 0`,
  `Missing span = 0`. If not, see
  [sail-voyage-debugging](../sail-voyage-debugging/SKILL.md).
- No secrets or token-shaped material appear anywhere the dashboard renders:
  metadata, events, stdout/stderr tails, or final printed JSON.
- The Voyage reaches a terminal `completed` or `failed` status; it does not
  remain `running`.

## Anti-patterns

- Creating one Voyage per subagent. Use agents inside one Voyage instead.
- Encoding input-specific data in `name`; use `metadata`.
- Bumping `version` for every run.
- Passing `voyage_series_id` through SDK code or visible URLs.
- Emitting full transcripts or command logs as event payloads.
- Logging credential file contents for debugging.
- Calling raw provider APIs and expecting native model-call rows.
- Calling `complete()` while background threads or model calls may still emit.
- Adding a fake artifact table, fake rerun button, or guest-owned runtime
  behavior in a skills/example change.

## Reference

- Minimal runnable example: [references/minimal-example.md](references/minimal-example.md)
- Multi-agent attribution detail: [references/multi-agent.md](references/multi-agent.md)
- Inference attribution: [sail-inference-with-voyage](../sail-inference-with-voyage/SKILL.md)
- Debugging: [sail-voyage-debugging](../sail-voyage-debugging/SKILL.md)
- Dashboard: <https://app.sailresearch.com/voyages>
