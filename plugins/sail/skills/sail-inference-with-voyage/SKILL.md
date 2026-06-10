---
name: sail-inference-with-voyage
description: Use when an instrumented Voyage calls Sail inference (the OpenAI-compatible Responses / Chat Completions API) and you need each model call — the LLM span — attributed to the active agent/span in the dashboard. Covers automatic Voyage/span/agent header propagation, background vs synchronous mode, wrapping a raw OpenAI client, and the immutable first-association-wins response_id contract. Not for authoring the Voyage itself (see sail-voyage) — only the inference-call leg.
---

# Sail Inference With Voyage

Use this pattern when a Voyage-instrumented process calls Sail inference
(Responses API or Chat Completions). Calls routed through the SDK's
`sail.inference.*` helpers automatically attach Voyage/span/agent headers
so model-call rows appear in the dashboard's Native Model Calls panel,
scoped to the right agent.

## When to use

- Any call to `sail.inference.responses.create()` /
  `sail.inference.chat.completions.create()` from inside a
  `sail.voyage.init(...)` context.
- Wrapping a raw OpenAI client when you can't switch to the SDK helper
  but still want Voyage attribution.

If your Voyage doesn't make inference calls, you don't need this skill.

## The contract

Every inference call inside an active Voyage gets these headers attached:

| Header                       | Purpose                                                  |
| ---------------------------- | -------------------------------------------------------- |
| `X-Sail-Voyage-Id`           | Required. Identifies which Voyage owns the call.         |
| `X-Sail-Voyage-Span-Id`      | Optional. Scopes the call to a specific span.            |
| `X-Sail-Voyage-Agent-Id`     | Optional. Scopes the call to a specific named agent.     |

The backend persists these into `voyage_model_calls` with the call's
`response_id` as the key.

**`response_id` is immutable, first-association-wins.** If you retry an
inference with the same `response_id`, the row stays attached to whichever
Voyage was active at first successful association — even if the retry
happens in a different Voyage.

## Copy-paste-ready example (SDK helper, automatic attribution)

```python
import sail

voyage = sail.voyage.init(name="agent-with-inference")

with voyage.agent("reviewer", name="Reviewer", role="reviewer"):
    with voyage.span("draft-response"):
        # Headers attached automatically because we're inside a voyage.
        response = sail.inference.responses.create(
            model="zai-org/GLM-5",
            input="Summarize this diff in one paragraph: ...",
            background=False,
            timeout=120,
        )
        voyage.event("response.drafted", payload={"response_id": response["id"]})

voyage.complete(message="done")
```

Nothing special needed. The Voyage/agent/span context propagates through
`sail.inference._merge_voyage_headers` → request headers → backend
attribution.

For a recurring production workflow, use the current series/version shape:

```python
voyage = sail.voyage.init(
    name="deep-research",
    version=3,
    metadata={"topic": "Voyages public launch"},
)
```

## Background mode

`sail.inference.responses.create(background=True)` returns the response
before the model finishes. Useful for long-running calls when you want
to poll or for parallel fan-out. Caveats:

- The call may complete _after_ the Voyage completes. The dashboard's
  Native Model Calls panel will still attribute the call correctly (the
  row was reserved at request time), but the terminal status of the
  model call may lag the Voyage's terminal status. This is the
  documented behavior, not a bug.
- For deterministic smokes, prefer `background=False`; a background call's
  terminal state can lag the Voyage's, which the dashboard reconciles after the
  fact.

## Wrapping a raw OpenAI client

If you can't switch to `sail.inference.*` (e.g., third-party library uses
the OpenAI client directly), attach headers explicitly:

```python
from openai import OpenAI
import sail

voyage = sail.voyage.init(name="raw-client")
cfg = sail.Config.from_env()
client = OpenAI(
    api_key=cfg.api_key,
    base_url=f"{cfg.api_url.rstrip('/')}/v1",
)

with voyage.agent("reviewer", name="Reviewer", role="reviewer"):
    with voyage.span("call"):
        response = client.responses.create(
            model="zai-org/GLM-5",
            input="...",
            extra_headers=sail.voyage.headers(),
        )
```

**`sail.voyage.headers()` is the public helper, and it attaches
`X-Sail-Voyage-Id` only.** Raw-client calls therefore get Voyage-level
attribution but still appear as unscoped in span/agent panels. Span/agent
attribution is applied internally by the SDK's `sail.inference.*` helpers —
route calls through them whenever scoped attribution matters.

## Common pitfalls

- **Calling `sail.inference.responses.create()` outside a Voyage.** It
  still works, but it does not create a `voyage_model_calls` row for any
  Voyage and will not appear in a Voyage dashboard. If you intended
  Voyage attribution, you forgot the `sail.voyage.init(...)`.
- **Mixing SDK and raw-client calls in the same agent.** Some calls get
  span/agent attribution (via the SDK), others get only Voyage-level
  (via `sail.voyage.headers()`). Inconsistent. Pick one and stick with
  it.
- **Reusing a `response_id` across Voyages.** The first attribution wins
  forever; subsequent calls are effectively orphaned from a Voyage
  perspective. Don't try to "fix" an attribution mistake by re-calling
  with the same id — create a new response.
- **Assuming non-Sail-routed inference calls show up in Voyages.** Calls
  routed through other providers (Anthropic, OpenAI direct) don't pass
  through Sail's backend and won't appear. Voyages only track Sail
  inference.
- **Parsing structured (JSON) replies without a fallback.** Models
  occasionally return prose, fenced code blocks, or a differently-shaped
  object. Validate the shape and degrade gracefully — defaults plus a
  `level="warn"` event — instead of letting one malformed reply crash the
  run, and only report a successful parse when real values were found.
- **Putting model output that contains secrets into Voyage payloads.**
  The dashboard has redaction at the SQL ingestion layer, but the safest
  pattern is to summarize / hash before storing.

## Verify it worked

Dashboard checklist:

- Overview → Native Model Calls panel: `Scoped > 0`, `Unscoped = 0`,
  `Missing span = 0`.
- Execution Trace and Waterfall: model rows reach terminal status
  (`responses · completed`, not `in_progress`). If they're stuck
  `in_progress`, see
  [sail-voyage-debugging section 4](../sail-voyage-debugging/SKILL.md).
- Waterfall model rows render solid, not striped.

SQL spot-check (requires direct DB access — Sail operators only; customers
should use the dashboard checks above):

```sql
SELECT response_id, voyage_id, span_id, agent_id, model
  FROM voyage_model_calls
 WHERE voyage_id = '<voy>';
```

Every row should have non-null `voyage_id`, `span_id`, `agent_id`.

## Reference

- Entrypoint skill: [sail-voyage](../sail-voyage/SKILL.md)
- Debugging stuck/unscoped model calls: [sail-voyage-debugging](../sail-voyage-debugging/SKILL.md)
