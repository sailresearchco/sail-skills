# Sail Skills

Agent Skills for building **observable background agents** on
[Sail](https://sailresearch.com) — instrument an agent run as a **Voyage**: a
trace of named agents, spans, and events, with every Sail model call and
sandbox command attributed to the right step, rendered in the
[Sail dashboard](https://app.sailresearch.com/voyages).

These skills follow the open [Agent Skills](https://agentskills.io) standard:
plain `SKILL.md` folders. The Claude Code plugin package is validated; Codex,
ChatGPT, and other Agent Skills-compatible tools can use the same skill folders
where they support importing standard skills. They contain **no hooks, scripts,
or MCP servers** — markdown only.

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

### Codex / ChatGPT

Codex and ChatGPT support Agent Skills, but this package has not yet been
smoke-tested there. Until then, treat the `skills/` folders as the portable
payload: copy them structure-intact (the skills cross-reference each other by
relative path) into the relevant skills library, or download this repository as
a ZIP and upload it where your plan/tool supports skill uploads.

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

## License

[Apache-2.0](./LICENSE)
