# Sail Skills

Agent Skills for building **observable background agents** and allocating
preemptible GPU compute on [Sail](https://sailresearch.com). Instrument an
agent run as a **Voyage**, delegate heavy work to Sail workers, or run a
checkpointed training job on a dedicated GPU VM.

These skills follow the open [Agent Skills](https://agentskills.io) standard:
plain `SKILL.md` folders, packaged as installable plugins for both **Claude
Code** and **Codex**. Other Agent Skills-compatible tools can use the same
skill folders where they support importing standard skills. Alongside the
markdown skills the plugin bundles a single MCP server declaration
(`.mcp.json`) that launches the published `sail[mcp]` package from PyPI via
`uvx` — the `sail-delegate` delegation server (see below). There are no hooks,
scripts, or Codex app connector, and nothing executes at install time.
Installing the plugin does not require a Sail API key; provision one only when
you actually delegate work or run code that calls Sail services.

## What's included

| Skill | Use it when |
| --- | --- |
| `sail-voyage` | Build or instrument any Voyage — the entrypoint. Series/version naming, agents, spans, events, Sailbox exec attribution, artifact retrieval, terminal lifecycle. Includes a minimal runnable example. |
| `sail-inference-with-voyage` | Attribute Sail inference model calls to the active agent/span (header propagation, background vs sync, raw-client fallback). |
| `sail-voyage-debugging` | A Voyage already ran but renders wrong in the dashboard — symptom → cause → fix. |
| `sail-fanout-policy` | Delegate or offload heavy coding/analysis to GLM workers on Sail via the `sail_delegate` and `sail_fanout` MCP tools — when to hand off vs. do it yourself, delegating autonomously under a standing preference, how to fan out independent subtasks, and how to apply the diffs workers return. |
| `sail-gpu-marketplace` | Allocate, connect to, and release a preemptible GPU VM, or recover a cooperative checkpointed job after interruption. |

## Delegating work to Sail workers

Installed in **Claude Code**, this plugin also adds the `sail-delegate` MCP
server: two tools, `sail_delegate` and `sail_fanout`, that hand a
self-contained coding or analysis task to a GLM worker running on Sail. Each
worker operates in an isolated copy of your project and returns a summary plus
a unified diff, which Claude checks and applies for you (ask to review diffs
first if you prefer) — your own conversation stays on your Claude plan while
the heavy token spend runs on your Sail account, and the two credentials never
mix. Tell Claude once to "delegate heavy work to Sail workers where
appropriate" and the `sail-fanout-policy` skill coaches it to do so
autonomously.

The server launches via `uvx`, so it needs [`uv`](https://docs.astral.sh/uv/)
installed and a Sail key (`sail auth login` or `SAIL_API_KEY`). See the
[delegation guide](https://docs.sailresearch.com/claude-code-delegation) for
setup, a first-run walkthrough, and troubleshooting.

## Install

### Claude Code (plugin)

```text
/plugin marketplace add sailresearchco/sail-skills
/plugin install sail@sail
```

Skills load automatically when relevant; invoke directly as `/sail:sail-voyage`.

Or, from a clone, without the marketplace:

```sh
claude --plugin-dir /path/to/sail-skills
```

### Codex (plugin)

```sh
codex plugin marketplace add sailresearchco/sail-skills
codex plugin add sail@sail
```

The skills then load by relevance, the same as in Claude Code.

### ChatGPT and other Agent Skills tools

The `skills/` folders are the portable payload. ChatGPT skill uploads have not
been smoke-tested with this package yet; where your plan supports uploading
skills, copy the folders structure-intact (they cross-reference each other by
relative path) or download this repository as a ZIP.

## Prerequisites

1. A Sail account and an org API key — create one at
   <https://app.sailresearch.com/api-keys>.
2. Provision the key one of two ways: `export SAIL_API_KEY=sk_...` in the
   environment your agent runs in, or run `sail auth login` (it stores the key
   under `~/.sail`, which the SDK reads the same way). `sail auth login` is the
   desktop-safe option — Dock-launched apps never inherit a shell's exported
   variables.
3. The Python SDK: `pip install sail` (use `pip install 'sail[mcp]'` for the
   `sail-delegate` delegation server).

## Quick start

Ask your agent:

> Build a small background research agent on Sail and make the whole run show
> up as a trace I can open in the dashboard — each step, the model calls it
> makes, and the sandbox commands it runs, attributed to the right part of the
> workflow.

The `sail-voyage` skill takes it from there.

## Contributing

This repo is a curated export of an internal source-of-truth tree — see
[CONTRIBUTING.md](./CONTRIBUTING.md) for how proposals and fixes flow.

## License

[Apache-2.0](./LICENSE)
