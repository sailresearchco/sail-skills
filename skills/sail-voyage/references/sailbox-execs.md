# Sailbox Exec Attribution

A **Sailbox is Sail's sandbox**. Only Sailbox execs are attributed into the
Voyage trace; work run elsewhere is invisible to the dashboard.

**A Sailbox is long-lived compute, not a per-call sandbox.** Create one box for
the task (or reconnect to an existing one with
`sail.Sailbox.get(sailbox_id)`), keep it running across every step, and bind
it to the Voyage once with `sail.voyage.run(..., sailbox_id=sb.sailbox_id)`. Run
many execs against that single box. When it is idle between bursts, `sb.pause()`
or `sb.sleep()` (state is checkpointed) and `sb.resume()` later; call
`sb.terminate()` only when the task is truly finished with it. Do **not** spin up
a Sailbox per exec, per function, or per `with` block — that per-call sandbox
model is slower, costlier, and is not how Sail is meant to be used.

Run Sailbox commands inside an active agent and span. Sail records `voyage_id`,
`span_id`, and `agent_id` on the native exec evidence automatically.

```python
def redact_tail(text, limit=2000):
    text = text or ""
    # Replace with your production token/secret redaction policy.
    return text[-limit:]


with voyage.agent("Executor", role="executor"):
    with voyage.span("run validation command"):
        req = sb.exec("cd /tmp/work && pytest -q", timeout=600)
        result = req.wait()
        voyage.event(
            "validation.command.completed",
            payload={
                "exec_request_id": req.exec_request_id,
                "exit_code": result.exit_code,
                "stdout_tail": redact_tail(result.stdout),
                "stderr_tail": redact_tail(result.stderr),
            },
        )
        if result.exit_code != 0:
            raise RuntimeError("validation command failed")
```

Rules: always set a non-zero `timeout`; record `exec_request_id` so manual
events dedupe against native rows; keep stdout/stderr tails bounded and
redacted; never put API keys, GitHub tokens, or bearer tokens in shell strings.

Do not rely on Sailbox APIs to auto-create Voyages, and do not pass the API key
into Sailbox commands to make guest code attach by default.

For real Python work in the guest (not just shell), pass a `@sail.function` to
`sb.exec(fn, *args)` — it runs in the Sailbox and returns the value, and still
produces an attributed exec row. Keep the function self-contained (imports
inside) so it ships cleanly to the guest. If a guest function imports
third-party packages, bake them into the image —
`sail.Image.debian_arm64.pip_install("matplotlib").build()` — rather than
installing them with a runtime exec, which is slower and adds a failure mode. To
retrieve an artifact the guest produced (a chart, a report file), read it back
on the controller with `data = sb.read(path)`, then record a bounded
`artifact.*` event (type, path hint, bytes, sha256) — not the bytes themselves.
See [minimal-example.md](minimal-example.md) for a complete runnable skeleton
that exercises every path above.
