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

Agents are SDK-level contexts, not separate processes. They are created by
entering `with sail.voyage.agent(slug, name=..., role=...)`. Multiple agents can
be active in one Voyage; nested agents push a stack.

## slug vs name vs role

- **`slug`** (first positional): the SDK-internal context key. Stable identifier
  for the agent context within the SDK; not user-facing.
- **`name`**: the human-readable instance label shown in the dashboard
  ("Reviewer", "ReviewerV2", "Critic-shadow"). Cockpit groups runs by name in
  the "Other runs of X" panel.
- **`role`**: the cohort taxonomy ("reviewer", "test_runner", "source_control",
  "executor"). The dashboard offers role as a categorical filter.

Both `name` and `role` are first-class; they answer different questions ("which
instance ran?" vs "what kind of work was done?"). Keep both stable across runs of
a series.

## Copy-paste-ready example

```python
import sail

voyage = sail.voyage.init(
    name="multi-agent-code-review",
    version=2,
    metadata={"pr_number": 1234},
)

sb = sail.Sailbox.create(
    app=sail.App.find(name="my-review-app", mint_if_missing=True),
    image=sail.Image.debian_arm64.apt_install("git").build(),
    name="multi-agent-review-demo",
)

# Agent 1: clone the repo (attributed to GitHub agent). Public repo here;
# private-repo credential injection requires Sail-provisioned org setup and
# is not part of the public v1 package. Never inline tokens in exec strings.
with voyage.agent("github", name="GitHub", role="source_control"):
    with voyage.span("clone"):
        clone_req = sb.exec(
            "git clone --depth 1 https://github.com/octocat/Hello-World.git /tmp/repo",
            timeout=120,
        )
        clone_req.wait()

# Agent 2: run checks (attributed to TestRunner agent).
with voyage.agent("test-runner", name="TestRunner", role="executor"):
    with voyage.span("run checks"):
        # Stand-in check that succeeds in any cloned repo; swap in your repo's
        # real test command (pytest, npm test, ...).
        test_req = sb.exec("cd /tmp/repo && python3 -m compileall -q .", timeout=600)
        test_req.wait()

# Agent 3: review (attributed to Reviewer agent, with a Sail inference call).
with voyage.agent("reviewer", name="Reviewer", role="reviewer"):
    with voyage.span("draft-comments"):
        response = sail.inference.responses.create(
            model="zai-org/GLM-5",
            input="Review the diff in /tmp/repo and write a one-paragraph summary.",
            background=False,
            timeout=120,
        )
        voyage.event("review.drafted", payload={"response_id": response["id"]})

voyage.complete(message="Multi-agent review finished")
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

SQL spot-check (requires direct DB access — Sail operators only; customers
should use the dashboard checks above):

```sql
SELECT DISTINCT agent_name FROM voyage_events WHERE voyage_id = '<voy>';
SELECT exec_request_id, agent_id, span_id, voyage_id FROM sailbox_execs WHERE voyage_id = '<voy>';
SELECT response_id, agent_id, span_id FROM voyage_model_calls WHERE voyage_id = '<voy>';
```

Expected shape:

- `sailbox_execs` rows created inside `with voyage.agent(...)` /
  `with voyage.span(...)` should have non-null `agent_id` and `span_id`.
- `voyage_model_calls` rows created through `sail.inference.*` inside an
  agent/span should have non-null `agent_id` and `span_id`.
- `voyage_events` includes top-level lifecycle events such as `voyage.started`,
  so do not require every event row to have agent/span ids. Check agent/span ids
  only for events you emitted inside agent/span contexts.

## Reference

- Back to the entrypoint skill: [sail-voyage](../SKILL.md)
