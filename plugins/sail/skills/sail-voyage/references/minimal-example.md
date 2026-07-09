# Minimal Example (reference)

The smallest complete Sail Voyage that still exercises every critical path:
`run → decorated agent/span → @sail.function exec in the Sailbox → sb.read →
scoped inference call → run() terminal state → dashboard handoff`.

The task is deliberately trivial (count words in a short string inside the
Sailbox, then have a model write a one-line takeaway). **Copy the shape, not the
task** — swap the guest work and the prompt for your real workflow.

Requires `SAIL_API_KEY` in the environment (create one at
<https://app.sailresearch.com/api-keys>).

```python
"""Minimal Sail Voyage example — copy the shape, not the task."""

import hashlib
import os

import sail


@sail.function()
def word_counts(text: str) -> dict:
    # Runs INSIDE the Sailbox. Keep imports inside so it ships cleanly by value.
    import json
    from collections import Counter

    counts = Counter(w.lower().strip(".,!?") for w in text.split())
    result = {"total": sum(counts.values()), "top": counts.most_common(5)}
    with open("/tmp/result.json", "w") as fh:
        json.dump(result, fh)
    result["path"] = "/tmp/result.json"
    return result


def main() -> None:
    if not os.environ.get("SAIL_API_KEY"):
        raise SystemExit(
            "set SAIL_API_KEY (create one at https://app.sailresearch.com/api-keys)"
        )

    text = "the quick brown fox the lazy dog the fox runs the fox"

    # Controller owns the Sailbox and the Voyage; the key never enters the guest.
    # One long-lived Sailbox for the whole task — created once, terminated once.
    sb = sail.Sailbox.create(
        app=sail.App.find(name="voyage-example", mint_if_missing=True),
        # Add .pip_install("pkg") before .build() if guest functions import
        # third-party packages (this example uses stdlib only).
        image=sail.Image.debian_arm64.build(),
        name="voyage-example",
        size="s",
    )

    # Each agent is a function with @sail.agent on it. Declare spans inside —
    # as inline `with` blocks for several sequential steps (Worker) or a stacked
    # @sail.span decorator for a single-span function (Analyst). Same frames.
    @sail.agent("Worker", role="executor")
    def worker() -> dict:
        with sail.voyage.span("count words"):
            result = sb.exec(word_counts, text, timeout=60)  # attributed exec row
            sail.voyage.event(
                "work.completed",
                payload={"total": result["total"]},  # bounded, no raw blobs
            )
        with sail.voyage.span("retrieve artifact"):
            data = sb.read(result["path"])  # pull the guest's file to the host
            sail.voyage.event(
                "artifact.result.ready",
                payload={
                    "path_hint": result["path"],
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                },
            )
        return result

    @sail.agent("Analyst", role="analyst")
    @sail.span("summarize")
    def analyst(top) -> None:
        # One scoped Sail inference call → model-call row, auto-attributed here.
        response = sail.inference.responses.create(
            model="zai-org/GLM-5.1-FP8",
            input=f"In one sentence, describe these word counts: {top}",
            background=False,
            timeout=120,
        )
        sail.voyage.event("summary.ready", payload={"response_id": response.get("id", "")})

    # The Sailbox is created before the Voyage, so guard it around the whole
    # run(): if entering run() fails (e.g. a transient Voyage API error) the box
    # already exists and must still be torn down. terminate() is idempotent, so
    # the two cleanup paths below never double-free.
    try:
        with sail.voyage.run(
            name="example-task",  # stable series name
            version=1,  # bump only when the workflow definition changes
            sailbox_id=sb.sailbox_id,
            metadata={"source": "minimal-example"},
        ) as voyage:
            try:
                result = worker()
                analyst(result["top"])
            finally:
                # Terminate INSIDE the run() block, before the terminal event,
                # so a cleanup failure becomes voyage.failed rather than a
                # "completed" Voyage on a leaked box.
                sb.terminate()
        # run() emits the terminal state on exit: completed on clean exit,
        # failed + re-raise on exception. No complete()/fail() here.
    finally:
        # Safety net for the case where run() never entered (idempotent). A
        # long-running service instead keeps one box warm and reuses it across
        # runs — see multi-agent.md.
        sb.terminate()

    print(voyage.id)
    print(voyage.dashboard_url)


if __name__ == "__main__":
    main()
```

## Verify it worked

Open the run from <https://app.sailresearch.com/voyages>:

- `example-task` series, one run, terminal status `completed`.
- Two agents: Worker (count + retrieve spans) and Analyst (summarize span).
- The `count words` step shows an attributed Sailbox exec row.
- The `summarize` step shows a scoped model-call row (`Scoped > 0`,
  `Missing span = 0`).
- `artifact.result.ready` carries a bounded payload (path hint, bytes, sha256) —
  not the file contents.
