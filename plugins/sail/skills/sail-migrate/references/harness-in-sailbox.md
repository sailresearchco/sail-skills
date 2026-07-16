# Run the Harness in a Sailbox

The in-place migration leaves the agent harness, meaning the controller loop
that calls models and executes commands, wherever it ran before. For a
compatible background workload, offer to move that harness into a Sailbox so
the workflow runs in one durable environment.

Benefits include:

- The run survives the operator's machine. Reconnect with
  `Sailbox.get(sailbox_id)`.
- The Sailbox can pause or sleep between bursts.
- Dependencies live in a repeatable custom image.
- A checkpoint can become a prepared template, and forks can fan it out.

## Decide whether the workload fits

Recommend the move for non-interactive, self-contained work such as scheduled
agents, queue workers, batch pipelines, evaluations, and long research or
coding tasks.

Do not blindly move:

- interactive servers that handle live user requests
- code coupled to a database, internal API, or private network a Sailbox
  cannot reach
- any workload the user wants to keep in its current deployment

This is an optional end-state after a working in-place migration, not a
prerequisite.

## Move the harness

1. Build a custom image containing the runtime and dependencies instead of
   installing them on every Sailbox. See
   <https://docs.sailresearch.com/sailbox-sdk-images>.
2. Put the code in the Sailbox. Clone a repository the Sailbox can reach, or
   transfer the working tree with the filesystem APIs.
3. Pass `SAIL_API_KEY` and other secrets through the `env=` mapping on `run`
   or `exec`. Never put secrets in shell strings, images, or repository files.
4. Start the harness with an explicit timeout. Stream output when the caller
   must observe it, or have a long-running worker write logs that later
   commands can inspect.
5. Store `sailbox_id` with the user's deployment state. Use one Sailbox per
   worker or task, pause or sleep it while idle, and terminate it when
   decommissioned.

## Verify parity

Run the same fixed input used for the in-place verification inside the
Sailbox. Confirm equivalent output and behavior. The controller's location
should be the only intentional difference.
