# Sail Skills

Agent Skills for building **observable background agents** on
[Sail](https://sailresearch.com) — instrument an agent run as a **Voyage**: a
trace of named agents, spans, and events, with every Sail model call and
sandbox command attributed to the right step, rendered in the
[Sail dashboard](https://app.sailresearch.com/voyages).

These skills follow the open [Agent Skills](https://agentskills.io) standard:
plain `SKILL.md` folders, packaged as installable plugins for both **Claude
Code** and **Codex**. Other Agent Skills-compatible tools can use the same
skill folders where they support importing standard skills. The package
contains **no hooks, scripts, or MCP servers** — markdown only.

## What's included

| Skill | Use it when |
| --- | --- |
| `sail-voyage` | Build or instrument any Voyage — the entrypoint. Series/version naming, agents, spans, events, Sailbox exec attribution, artifact retrieval, terminal lifecycle. Includes a minimal runnable example. |
| `sail-inference-with-voyage` | Attribute Sail inference model calls to the active agent/span (header propagation, background vs sync, raw-client fallback). |
| `sail-voyage-debugging` | A Voyage already ran but renders wrong in the dashboard — symptom → cause → fix. |

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
2. `export SAIL_API_KEY=sk_...` in the environment your agent runs in (the SDK
   reads the environment directly).
3. The Python SDK: `pip install sail-sdk`.

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
