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
  `sail.voyage.run(...)` (or `create(...)`) context.
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

Sail records the model-call association with the call's `response_id` as
the key.

**`response_id` is immutable, first-association-wins.** If you retry an
inference with the same `response_id`, the existing association stays
attached to whichever Voyage was active at first successful association —
even if the retry happens in a different Voyage.

## Copy-paste-ready example (SDK helper, automatic attribution)

```python
import sail


@sail.agent("Reviewer")
@sail.span("draft-response")
def draft():
    # Headers attached automatically because a Voyage is active; the call
    # auto-attributes to this agent/span.
    response = sail.inference.responses.create(
        model="zai-org/GLM-5",
        input="Summarize this diff in one paragraph: ...",
        background=False,
        timeout=120,
    )
    sail.voyage.event("response.drafted", payload={"response_id": response["id"]})


with sail.voyage.run(name="agent-with-inference", version=1):
    draft()
```

Nothing special needed. The Voyage/agent/span context propagates through
`sail.voyage.headers()` → request headers → backend attribution.

**No active span?** The wrapper synthesizes one automatically (an
"auto-span", marked `_auto` and chipped in the cockpit), named after your
calling function — so wrapper calls never land as `Missing span`. Explicit
spans always win; `SAIL_VOYAGE_AUTO_SPANS=0` disables synthesis. Raw
clients don't get synthesis (headers are request-time only) — wrap those
calls in a span yourself when scoping matters.

For a recurring production workflow, use the current series/version shape:

```python
with sail.voyage.run(
    name="deep-research",
    version=3,
    metadata={"topic": "Voyages public launch"},
):
    ...
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

If you can't switch to `sail.inference.*` (e.g., a third-party library uses
the OpenAI client directly), wrap the client once with
`sail.voyage.wrap_openai()` — every call then computes the attribution
headers at call time and un-spanned calls get the same synthesized
auto-spans as `sail.inference.*`:

```python
from openai import OpenAI
import sail

cfg = sail.Config.from_env()
client = sail.voyage.wrap_openai(
    OpenAI(api_key=cfg.api_key, base_url=f"{cfg.api_url.rstrip('/')}/v1")
)

with sail.voyage.run(name="raw-client", version=1) as voyage:
    with voyage.agent("Reviewer"):
        with voyage.span("call"):
            response = client.responses.create(model="zai-org/GLM-5", input="...")
```

`wrap_openai` wraps `responses.create`, `responses.retrieve`, and
`chat.completions.create` in place — every holder of that client object
sees attributed calls, so wrap a dedicated client if some callers must stay
unattributed. It is idempotent, supports `AsyncOpenAI` (the auto-span
covers the awaited request), and follows the process-global current Voyage
per call (pass `voyage=` to pin one).

For any non-OpenAI-style HTTP client, attach
`sail.voyage.headers()` yourself — it carries the full attribution context
(voyage id plus the span and agent active at the moment you call it).
**Compute it per call, never once at client construction**:
`OpenAI(default_headers=sail.voyage.headers())` freezes whatever context
was active at construction onto every later call — constructed inside a
span, that pins the wrong span to your whole run. (`wrap_openai` makes this
mistake unrepresentable; prefer it whenever the client is OpenAI-style.)

## Common pitfalls

- **Calling `sail.inference.responses.create()` outside a Voyage.** It
  still works, but it does not create any Voyage dashboard model-call
  association. If you intended Voyage attribution, you forgot to open a
  Voyage (`sail.voyage.run(...)`).
- **Baking `sail.voyage.headers()` into `default_headers` at client
  construction.** That snapshots one span/agent context onto every later
  call. Pass `extra_headers=sail.voyage.headers()` per call instead.
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
  Dashboard redaction is a backstop, not a design pattern. Summarize, hash, or
  omit sensitive values before storing them in Voyage events or metadata.

## Verify it worked

Dashboard checklist:

- Overview → Native Model Calls panel: `Scoped > 0`, `Unscoped = 0`,
  `Missing span = 0`.
- Execution Trace and Waterfall: model rows reach terminal status
  (`responses · completed`, not `in_progress`). If they're stuck
  `in_progress`, see
  [sail-voyage-debugging section 4](../sail-voyage-debugging/SKILL.md).
- Waterfall model rows render solid, not striped.
- Each model call row shows the expected agent/span. If a row is unscoped,
  move the inference call inside `@sail.agent(...)` and `@sail.span(...)`, or
  use the SDK helper / `wrap_openai()` path so headers are computed at request
  time.

## Reference

- Entrypoint skill: [sail-voyage](../sail-voyage/SKILL.md)
- Debugging stuck/unscoped model calls: [sail-voyage-debugging](../sail-voyage-debugging/SKILL.md)
