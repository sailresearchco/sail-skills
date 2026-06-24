# Multi-Agent Attribution (reference)

Reference for [sail-voyage](../SKILL.md). Use this when one Voyage involves
multiple cooperating agents — e.g. a "Reviewer" that reads code and a
"TestRunner" that runs tests inside a shared Sailbox. Each agent gets its own
spans, events, model calls, and exec rows in the dashboard, but they all belong
to one Voyage.

Common cases:

- A code review agent with a Reviewer / TestRunner / GitHub-poster split.
- An eval harness where different judges score the same response.
- Any controller process where you want the dashboard to render "this work was
  done by agent X, that work was done by agent Y."

For multi-process / multi-machine cases (subprocesses, distributed runners), see
the "Child and multi-process runs" section in [sail-voyage](../SKILL.md).

## Mental model

```
Voyage (one per task)
  └── Agent (one per role-named participant)
        └── Span (one per logical step the agent does)
              └── Event, model call, exec
```

Agents are SDK-level contexts, not separate processes. Declare each with
`@sail.agent("Agent Name", role=...)` on its function (or `with
voyage.agent("Agent Name", role=...)` inline). Multiple agents can be active in
one Voyage; nested agents push a stack.

## name, role, and slug

- **name** (the only required argument): the human-readable identity shown in
  the dashboard ("Reviewer", "ReviewerV2", "Critic-shadow"). The cockpit groups
  runs by name in the "Other runs of X" panel. The stable attribution key is
  derived from it automatically (lowercased, ASCII, hyphenated — "Source
  Researcher" → `source-researcher`).
- **`role=`** (optional): the cohort taxonomy ("reviewer", "test_runner",
  "source_control", "executor"). The dashboard offers role as a categorical
  filter across workflows. Freeform — pick a vocabulary and keep it stable.
- **`slug=`** (optional, advanced): pins the attribution key explicitly. Use it
  when you rename an agent's display name but want its history to stay one
  identity, or when a child process must attach as the same agent.

Renaming the display name otherwise creates a new agent identity. Keep names
and roles stable across runs of a series.

## Copy-paste-ready example

```python
import sail

# One long-lived Sailbox, shared by all three agents below. A real review
# service reconnects to a kept-warm box (`Sailbox.connect`) and reuses it across
# PRs rather than creating one per run.
sb = sail.Sailbox.create(
    app=sail.App.find(name="my-review-app", mint_if_missing=True),
    image=sail.Image.debian_arm64.apt_install("git").build(),
    name="multi-agent-review-demo",
)


# Agent 1: clone the repo (attributed to GitHub agent). Public repo here —
# never inline tokens in exec strings.
@sail.agent("GitHub", role="source_control")
@sail.span("clone")
def clone_repo():
    sb.exec(
        "git clone --depth 1 https://github.com/octocat/Hello-World.git /tmp/repo",
        timeout=120,
    ).wait()


# Agent 2: run checks (attributed to TestRunner agent).
@sail.agent("TestRunner", role="executor")
@sail.span("run checks")
def run_checks():
    # Stand-in check that succeeds in any cloned repo; swap in your repo's real
    # test command (pytest, npm test, ...).
    sb.exec("cd /tmp/repo && python3 -m compileall -q .", timeout=600).wait()


# Agent 3: review (attributed to Reviewer agent, with a Sail inference call).
@sail.agent("Reviewer", role="reviewer")
@sail.span("draft-comments")
def review():
    response = sail.inference.responses.create(
        model="zai-org/GLM-5.1-FP8",
        input="Review the diff in /tmp/repo and write a one-paragraph summary.",
        background=False,
        timeout=120,
    )
    sail.voyage.event("review.drafted", payload={"response_id": response["id"]})


with sail.voyage.run(
    name="multi-agent-code-review",
    version=2,
    sailbox_id=sb.sailbox_id,
    metadata={"pr_number": 1234},
):
    clone_repo()
    run_checks()
    review()
# run() emits the terminal state on exit. The shared Sailbox is long-lived —
# terminate it when the review service shuts down, not per run.
```

## What this gives you

In `/voyages`, this run appears under the `multi-agent-code-review` series and
version 2. In the run detail page:

- **Overview** shows three agents: GitHub, TestRunner, Reviewer.
- **Execution Trace** shows three agent groups; each agent's spans and events
  nest underneath in Agent view.
- **Execution Trace** and **Waterfall** show two exec rows (clone, checks)
  attributed to the right agents and spans.
- **Native model calls panel** shows the Reviewer agent's inference call with
  `Scoped > 0`, `Missing span = 0`.

Same Voyage. Same Sailbox. Three agents.

## Common pitfalls

- **Reusing one agent context for multiple roles.** Don't put a clone step
  inside the Reviewer agent context. Spans and execs inherit whichever agent is
  currently active; mis-attribution is hard to undo in the dashboard.
- **Hardcoding names like "Agent 1".** Use real role-like names. The dashboard
  groups runs by name; "Agent 1" buckets everything together unhelpfully.
- **Changing `name` for each input.** The Voyage `name` is the series. Keep it
  stable across runs and put PR/repo/topic context in `metadata`.
- **Bumping `version` for each run.** Version tracks workflow changes, not run
  count.
- **Mixing role taxonomies across runs.** Pick a role vocabulary and stick with
  it: "reviewer" / "test_runner" / "executor" / "source_control" / "planner"
  cover most cases.
- **Spawning subprocesses without child attach.** A subprocess that doesn't read
  `SAIL_VOYAGE_ID` creates its own orphaned Voyage. See the "Child and
  multi-process runs" section in [sail-voyage](../SKILL.md).
- **Calling `voyage.complete()` from inside a nested agent context.** Complete at
  the top level, after all agent blocks have exited. The first terminal status
  wins.

## Verify it worked

Dashboard checklist:

- Overview → Agents panel lists every name you used.
- Execution Trace Agent view shows one nested block per agent, with spans/events
  underneath.
- Exec evidence rows have `Agent: <name>` / `Span: <id>` populated.
- Native model calls panel: `Scoped` count equals the total inference calls;
  `Missing span` is zero.

Expected dashboard shape:

- Sailbox exec rows created inside `with voyage.agent(...)` /
  `with voyage.span(...)` show the expected agent and span.
- Model calls created through `sail.inference.*` inside an agent/span show the
  expected agent and span.
- Top-level lifecycle events such as `voyage.started` may appear outside an
  agent/span. Check attribution on the events, model calls, and execs emitted
  from your agent/span code.

## Reference

- Back to the entrypoint skill: [sail-voyage](../SKILL.md)
