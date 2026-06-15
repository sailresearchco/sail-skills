# Child And Multi-Process Voyages

Keep one Voyage per logical task. A subprocess that does not read
`SAIL_VOYAGE_ID` creates its own orphaned Voyage. Use child attach only when the
child already receives credentials through a secure channel:

```python
# parent
import os, subprocess, sys
subprocess.run(
    [sys.executable, "child.py"],
    env={**os.environ, **sail.voyage.child_env()},
    check=True,
)

# child
import sail
sail.voyage.attach()  # joins SAIL_VOYAGE_ID when SAIL_API_KEY is present
```

`child_env()` carries the Voyage id plus the active `agent()` context as the
child's `SAIL_AGENT_*` defaults; it returns `{}` keyless.

`SAIL_VOYAGE_ID` is correlation only; `SAIL_API_KEY` still authorizes event
delivery. Do not use this pattern to smuggle credentials into Sailbox guest
commands.
