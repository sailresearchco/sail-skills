---
name: sail-voyage-debugging
description: 'Use when a Voyage already ran but renders wrong in the dashboard: missing from the series list, no events, agents not appearing, model calls (LLM spans) stuck in_progress, no Sailbox exec evidence, or "Unscoped" / "Missing span" counts. A symptom→cause→fix diagnostic playbook grounded in real rollout failure modes. Use this to fix an existing trace, not to author one (see sail-voyage).'
---

# Sail Voyage Debugging

Use this when a Voyage you expected to see in the dashboard either doesn't
appear, appears incomplete, or shows misleading state. Below: the
high-frequency failure modes, what they look like, how to diagnose, and
how to fix.

## Diagnostic flow

```
Voyage missing from dashboard list ──► section 1
   │
   ├─ Voyage shows but Overview says "no events" ──► section 2
   │
   ├─ Events present but agents missing ──► section 3
   │
   ├─ Model calls stuck "in_progress" / striped ──► section 4
   │
   ├─ No Sailbox exec evidence when you expected execs ──► section 5
   │
   ├─ "Unscoped" model calls > 0 ──► section 6
   │
   └─ Voyage never reaches terminal status ──► section 7
```

## 1. Voyage missing from dashboard list

**Symptoms:** You called `sail.voyage.create(...)` but the Voyage doesn't
appear at the env-qualified dashboard URL, for example
`app.sailresearch.com/prod/voyages/<voyage_id>`.

**Most likely causes:**

- **Wrong org.** The dashboard scopes to your active Clerk org. If the
  API key belongs to a different org, the Voyage is invisible to your
  current login.
- **Wrong series name.** `/voyages` groups by exact `name`. If you changed
  capitalization or embedded the input/date in `name`, the run may be under a
  different series than expected.
- **Missing API key.** If `SAIL_API_KEY` is unset, the SDK creates a no-op
  Voyage and emits one `RuntimeWarning` per process saying telemetry is
  disabled. Look for it in stderr.
- **Invalid API key.** A 401 from `voyage.create()` raises `VoyageHTTPError`;
  the Voyage was never created. Look for the exception in stderr.

**Diagnose:**

```python
import sail
voyage = sail.voyage.create(name="diag")
print("voyage_id =", sail.voyage.id())          # None if telemetry is disabled
print("dashboard_url =", sail.voyage.dashboard_url())
```

If `voyage_id` is None at the top of your script, the SDK degraded to a
no-op Voyage (and warned why on stderr).
Check `SAIL_API_KEY`, and try a single `/v1/models` curl
against the API endpoint to confirm the key works there.

## 2. Voyage exists but Overview says "no events"

**Symptoms:** Voyage row exists; Overview shows agents/events as 0.

**Most likely causes:**

- **Process exited before flush.** Voyage events are buffered. Calling
  `sys.exit(0)` or letting the process die mid-flight can drop events.
  Always call `voyage.complete()` (or `voyage.fail()`) before exit.
- **Voyage was created in a different process than the one emitting
  events.** Subprocess didn't read `SAIL_VOYAGE_ID`; it created its own
  Voyage and emitted events there.

**Diagnose:**

```python
voyage.flush()   # force buffered events to write before assertion
```

If events appear after explicit flush but not before, your process was
exiting too early.

## 3. Events present but agents missing

**Symptoms:** Events fire but the Overview's "Agents" panel is empty or
wrong.

**Most likely cause:** events were emitted outside any
`with voyage.agent(...)` block. The dashboard derives the agent list
from stored event attribution, which is populated from the active agent
context at event time.

**Fix:** wrap event/span emission in `with voyage.agent("Agent Name", role=...)`.
See [sail-voyage multi-agent reference](../sail-voyage/references/multi-agent.md).

## 4. Model calls stuck "in_progress" / striped in waterfall

**Symptoms:** The Voyage waterfall shows model-call rows as striped /
"partial" / `in_progress` even after the Voyage completed.

**Known issue:** the dashboard reconciles terminal state on the read path, but a
model call's producer-side close event (from the Responses streaming path) can be
intermittently late or missing — for synchronous and background calls alike — so
the row can look stuck.

**Workaround:**

- Prefer `background=False` on `sail.inference.responses.create()`; the
  synchronous path tends to be more reliable about terminal-state events, though
  it is not immune.
- Wait ~30-60s before checking the dashboard; the reconciled terminal state
  eventually appears.

## 5. No Sailbox exec evidence when you expected execs

**Symptoms:** You ran `Sailbox.exec()` inside a Voyage but Execution Trace,
Waterfall, or native exec evidence views do not show the command.

**Most likely causes:**

- **Sailbox isn't bound to the Voyage.** Either pass `sailbox_id=` to
  `voyage.create()` at start, or run the exec inside a Voyage agent/span
  context. Sail associates the exec row through request metadata from the
  active context.
- **The exec dispatched outside any agent context.** The SDK can synthesize
  an auto-span for an un-spanned exec, but it does not invent an agent. Put the
  exec inside `@sail.agent(...)` / `with voyage.agent(...)` so the dashboard can
  show who caused the work.
- **The request never reached `.wait()`.** Foreground Sailbox exec auto-spans
  close when `.wait()` observes the result. If you dispatch and drop the handle,
  the dashboard may show a partial started span.

**Diagnose in the dashboard:** open the Voyage detail page, then check
Execution Trace and the Sailbox/native exec evidence view. The exec should show
the expected Sailbox id, command preview, agent name, and span. If the command
is present but agent/span are missing, move the `exec(...).wait()` call inside
the intended agent/span function and re-run.

## 6. "Unscoped" model calls > 0

**Symptoms:** Overview's Native Model Calls panel shows `Unscoped: N` or
`Missing span: N` with N > 0.

**Most likely causes:**

- **The call ran outside any `agent()` / `span()` context.** Headers carry
  whatever context is active at call time; with none active, only the
  voyage id is attached. Wrap the call:
  `with voyage.agent("Analyst"): with voyage.span("score"): ...`
- **A raw client snapshotted headers at construction.**
  `OpenAI(default_headers=sail.voyage.headers())` freezes the context that
  was active when the client was built — usually none, or worse, the wrong
  span. Wrap the client instead; headers are then computed per call and
  un-spanned calls get synthesized auto-spans, same as `sail.inference.*`:

```python
from openai import OpenAI
import sail

cfg = sail.Config.from_env()
client = sail.voyage.wrap_openai(
    OpenAI(api_key=cfg.api_key, base_url=f"{cfg.api_url.rstrip('/')}/v1")
)

with voyage.agent("Analyst"):
    with voyage.span("score"):
        response = client.responses.create(model="zai-org/GLM-5.1-FP8", input="...")
```

  For a non-OpenAI-style client, pass `extra_headers=sail.voyage.headers()`
  per call — the helper carries the full attribution context (voyage id
  plus the active span and agent) as of the moment you call it.

## 7. Voyage never reaches terminal status

**Symptoms:** Voyage Overview keeps saying "in progress" indefinitely.

**Most likely causes:**

- Process exited without calling `voyage.complete()` or `voyage.fail()`.
- An exception was raised inside a `with voyage.span(...)` block and
  bypassed the terminal call. Wrap the whole script body in
  `try/except` and call `voyage.fail(error_type=..., message=...)` on
  exception.
- The terminal flush could not deliver. `complete()`/`fail()` never raise
  on delivery failure — they warn on stderr and leave the event buffered
  for background/atexit retry. If the process exits immediately on a dead
  network, the event can be lost; check stderr for the
  `could not deliver voyage.completed` warning, and call `voyage.flush()`
  after the terminal call when you need raise-on-failure confirmation.

**Pattern:**

```python
voyage = sail.voyage.create(name="task")
try:
    do_work()
    voyage.complete(message="ok")
except Exception as exc:
    voyage.fail(error_type=exc.__class__.__name__, message=str(exc))
    raise
```

## 8. Spans you don't remember writing ("auto" chips)

**Symptoms:** the Execution Trace shows spans with an "auto" chip (dashed
badge), or Waterfall bars with diagonal striping, that your code never
declared.

**This is expected:** those are auto-spans — the SDK
synthesizes a span around any Sail inference call or Sailbox exec made with
no active span, named after your calling function when derivable. They mean
your work was captured and scoped even where you declared nothing. They are
not a bug and not double-counting: synthesis never happens inside an
explicit span.

- To take ownership of a step's name/structure, wrap it in `@sail.span()` /
  `with voyage.span(...)` — explicit always wins and the auto chip
  disappears.
- To disable synthesis entirely, set `SAIL_VOYAGE_AUTO_SPANS=0`; rows then
  fall back to `Missing span` as before.
- Auto-spans never invent agents; an agent-less auto-span renders under the
  system/unattributed lane until you declare an agent.

## When all else fails

- Check stderr first: every degradation (disabled telemetry, dropped
  events, stubbed oversized payloads, undelivered terminal events) emits
  one `RuntimeWarning` per process unconditionally.
- Re-run with the SDK debug env: `SAIL_VOYAGE_DEBUG=1` for per-occurrence
  repeats of those warnings.
- Compare against a known-good run: run a minimal Voyage you trust (see the
  example in [sail-voyage](../sail-voyage/SKILL.md)) and confirm it renders
  correctly before assuming the dashboard is broken.

## Reference

- Entrypoint skill: [sail-voyage](../sail-voyage/SKILL.md)
- Dashboard: <https://app.sailresearch.com/voyages>
