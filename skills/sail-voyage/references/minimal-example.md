# Minimal Example (reference)

The smallest complete Sail Voyage that still exercises every critical path:
`init → agent → span → event → @sail.function exec in the Sailbox → sb.read →
scoped inference call → terminal complete/fail → dashboard handoff`.

The task is deliberately trivial (count words in a short string inside the
Sailbox, then have a model write a one-line takeaway). **Copy the shape, not the
task** — swap the guest work and the prompt for your real workflow.

Requires `SAIL_API_KEY` in the environment (create one at
<https://app.sailresearch.com/api-keys>; `SAIL_MODE` defaults to `prod`).

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
    sb = sail.Sailbox.create(
        app=sail.App.find(name="voyage-example", mint_if_missing=True),
        # Add .pip_install("pkg") before .build() if guest functions import
        # third-party packages (this example uses stdlib only).
        image=sail.Image.debian_arm64.build(),
        name="voyage-example",
        cpu=1,
        memory_mib=1024,
    )
    voyage = None
    try:
        # Create the Voyage inside the cleanup guard: if init fails, the finally
        # block still terminates the Sailbox instead of leaking it.
        voyage = sail.voyage.init(
            name="example-task",  # stable series name
            version=1,  # bump only when the workflow definition changes
            sailbox_id=sb.sailbox_id,
            metadata={"source": "minimal-example"},
        )

        # Worker agent: do the work in the Sailbox → attributed exec row.
        with voyage.agent("Worker", role="executor"):
            with voyage.span("count words"):
                result = sb.exec(word_counts, text, timeout=60)
                voyage.event(
                    "work.completed",
                    payload={"total": result["total"]},  # bounded, no raw blobs
                )
            with voyage.span("retrieve artifact"):
                data = sb.read(result["path"])  # pull the guest's file to the host
                voyage.event(
                    "artifact.result.ready",
                    payload={
                        "path_hint": result["path"],
                        "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    },
                )

        # Analyst agent: one scoped Sail inference call → model-call row.
        with voyage.agent("Analyst", role="analyst"):
            with voyage.span("summarize"):
                response = sail.inference.responses.create(
                    model="zai-org/GLM-5",
                    input=f"In one sentence, describe these word counts: {result['top']}",
                    background=False,
                    timeout=120,
                )
                voyage.event(
                    "summary.ready",
                    payload={"response_id": response.get("id", "")},
                )

        # Clean up the Sailbox BEFORE the terminal event, so a cleanup failure
        # becomes voyage.failed rather than a "completed" Voyage on a crashed run.
        sb.terminate()
        sb = None
        voyage.complete(message="example task complete")
    except Exception as exc:
        if voyage is not None:
            voyage.fail(error_type=exc.__class__.__name__, message=str(exc))
        raise
    finally:
        if sb is not None:
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
