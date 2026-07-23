# Sail Skills

Use Sail models from the coding agent you already work in. The Sail plugin can
delegate scoped coding work, request a read-only review, or give a Sail model
an entire task. It also includes skills for migrating applications to Sail,
building observable agents, and using preemptible GPU compute.

The plugin uses standard `SKILL.md` folders and one `sail-delegate` MCP server.
The same skill payload and server launch command ship for Claude Code and local
Codex sessions. GLM-5.2 is the only curated worker choice in this release. The
delegation tools keep an optional model argument for future additions, but the
plugin does not present a model picker yet.

Installation, usage, and troubleshooting are covered in
[Sail for coding agents](https://docs.sailresearch.com/coding-agents).

## Included skills

| Skill | Use it when |
| --- | --- |
| `sail-subs` | Automatically delegate suitable scoped work while the host keeps ownership of planning, integration, and verification. |
| `sail-review` | Ask for an on-demand, read-only review with severity-ordered findings and file references. |
| `sail-charter` | Explicitly give a Sail model ownership of an entire coding task. |
| `sail-update` | Update the installed Sail plugin from the current coding agent and verify its version. |
| `sail-migrate` | Migrate an application's inference or third-party sandbox execution to Sail while preserving behavior. |
| `sail-voyage` | Build or instrument a Voyage with agents, spans, events, model-call attribution, Sailbox commands, and terminal lifecycle. |
| `sail-inference-with-voyage` | Attribute Sail inference calls to the active Voyage, agent, and span. |
| `sail-voyage-debugging` | Diagnose a Voyage that ran but appears incomplete or incorrect in the dashboard. |
| `sail-gpu-marketplace` | Allocate, connect to, and release a preemptible GPU VM, or recover checkpointed work after an interruption. |

## Install

### Claude Code

```text
/plugin marketplace add sailresearchco/sail-skills
/plugin install sail@sail
```

Skills load when relevant. You can also invoke one directly, such as
`/sail:sail-review`.

### Codex

```sh
codex plugin marketplace add sailresearchco/sail-skills
codex plugin add sail@sail
```

The Codex package includes all nine skills and the `sail-delegate` MCP server.
The server works in local Codex app, CLI, and IDE sessions. Hosted Codex
sessions cannot run the bundled local stdio server. In app and IDE sessions,
the Sail skills pass the active workspace path with each tool call so the
server does not depend on its process working directory. Claude Code supplies
the selected project root directly to plugin MCP servers, including in its
desktop app.

## Authentication

Installing the plugin does not require a Sail API key. Authenticate before the
first delegation:

```sh
sail auth login
```

If you need the CLI first:

```sh
curl -fsSL https://cli.sailresearch.com/install.sh | sh
```

You can instead export `SAIL_API_KEY` before starting your coding agent. A
stored login is more reliable for desktop apps because they may not inherit
shell variables.

## Update

On version `0.3.0` or later, use `/sail:sail-update` in Claude Code or
`$sail-update` in Codex. The coding agent runs the client update commands and
verifies the installed version. Reload plugins or start a new session when it
finishes.

If the update skill is missing, follow the manual update instructions in
[Sail for coding agents](https://docs.sailresearch.com/coding-agents) once to
reach `0.3.0` or later.

## Contributing

This repository is a curated export from Sail's source tree. See
[CONTRIBUTING.md](./CONTRIBUTING.md) before proposing a change.

## License

[Apache-2.0](./LICENSE)
