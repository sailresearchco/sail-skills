---
name: sail-update
description: Use when the user asks to update, upgrade, refresh, or reinstall the installed Sail plugin in Claude Code or Codex. Run the current host client's update commands, verify the installed version, and explain that a new session or reload is needed before the updated skills and tools appear. This does not update Sail SDK dependencies or change plugin configuration.
---

# Sail Update

Update the Sail plugin only when the user asks. Run the commands for them rather
than returning a list of commands to paste.

## Confirm the current install

Use the current coding host. Do not guess based on which executables happen to
be installed. Check that `sail@sail` is installed and record its version:

- In Claude Code, run `claude plugin list --json`.
- In Codex, run `codex plugin list --marketplace sail --json`.

If Sail is not installed, say that installation is required instead of claiming
an update. Do not silently install it or rewrite marketplace configuration.

## Update Claude Code

Run these shell commands:

```bash
claude plugin marketplace update sail
claude plugin update sail@sail
claude plugin list --json
```

Fully restart Claude Code after the update. `/reload-plugins` refreshes the
skills, but a session's running `sail-delegate` MCP server keeps the runtime
it started with, and new skills driving an old runtime fail in confusing
ways. Only a restart relaunches the server on the updated version.

## Update Codex

Run:

```bash
codex plugin marketplace upgrade sail --json
codex plugin list --marketplace sail --json
```

Upgrading a configured Git marketplace refreshes the installed plugin cache.
If Codex reports that `sail` is a local marketplace, reinstall from its current
snapshot with `codex plugin add sail@sail --json`; do not edit marketplace files
or Codex configuration by hand.

Codex loads the new skills in a new thread, but the app's background process
keeps any running `sail-delegate` MCP server on the version it started with,
and new skills driving an old runtime fail in confusing ways. After the
upgrade, fully quit and reopen the Codex app rather than only starting a new
thread.

## Report the result

Compare the version before and after the update. Report one of these outcomes:

- Updated from the old version to the new version.
- Already current at the reported version.
- Update failed, with the specific failing command and a short error summary.

Do not claim success from a zero exit code alone. Verify the installed version.
Do not uninstall Sail as a fallback without asking because that can remove the
working installation before a replacement is ready.
