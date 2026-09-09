#!/usr/bin/env python3
"""Launch sail-delegate without refreshing package metadata on every start.

The MCP server is the ``sail[mcp]`` distribution from PyPI, pinned exactly to
the plugin's own version (see ``RUNTIME_VERSION``). It is normally launched
through ``uvx`` like this::

    uvx --python '>=3.10' --from 'sail[mcp]==<version>' \\
        python -I -m sail.mcp

Historically the plugin also passed ``--refresh-package sail`` to ``uvx`` on
every launch so a stale index could never hide a freshly released exact pin.
The cost is that uv re-fetches Sail's package metadata on *every* launch,
which is slow enough that coding agents (Codex, Claude Code) sometimes give up
and silently omit the optional MCP server.

This launcher keeps the exact pinned runtime while avoiding a forced metadata
refresh on the ordinary warm-cache path:

* Probe whether the pinned runtime already resolves from uv's local cache
  using ``uvx --offline``, which never touches the network.
* If it does, exec straight into the server with no ``--refresh-package``.
* If it does not (e.g. uv's index metadata is stale and hides a freshly
  published exact pin), perform one targeted ``uvx --refresh-package sail``
  recovery, then exec the same warm command.

stdin/stdout carry the MCP JSON-RPC protocol and are never written to by this
script; all diagnostics go to stderr. The server ``execv``-replaces this
process, so there is no code path after a normal MCP session ends that could
retry a launch.
"""

from __future__ import annotations

import os
import subprocess

# Keep in sync with .claude-plugin/plugin.json "version". Declaring the
# runtime exactly means an existing uv cache can never silently serve an older
# Sail runtime than the plugin manifests. Bump here on every plugin version
# bump (see SKILL_MAINTENANCE.md).
RUNTIME_VERSION = "0.11.4"
RUNTIME_SPEC = f"sail[mcp]=={RUNTIME_VERSION}"
UVX_PREFIX = ["uvx", "--python", ">=3.10"]

#: The MCP server entrypoint, launched through uvx with no metadata refresh.
WARM_COMMAND = [
    *UVX_PREFIX,
    "--from",
    RUNTIME_SPEC,
    "python",
    "-I",
    "-m",
    "sail.mcp",
]


def pinned_available_offline() -> bool:
    """Return True if the pinned runtime resolves from uv's local cache.

    Runs ``uvx --offline`` which disables network access; it only succeeds
    when the exact pin is already present in uv's local cache/metadata. Any
    ``OSError`` (for example uvx not installed) is reported as "available" so
    the subsequent real launch surfaces the real error instead of this probe.
    """
    probe = [
        *UVX_PREFIX,
        "--offline",
        "--from",
        RUNTIME_SPEC,
        "python",
        "-c",
        "pass",
    ]
    try:
        return (
            subprocess.call(
                probe,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            == 0
        )
    except OSError:
        return True


def recover_stale_metadata() -> None:
    """Re-fetch just Sail's metadata so the pinned release becomes visible.

    uv caches index metadata and only refreshes it after a TTL. A freshly
    published exact pin can therefore be temporarily invisible, which looks
    exactly like a missing package. ``--refresh-package sail`` forces uv to
    re-query just Sail's metadata so the subsequent warm launch resolves.
    Best-effort: any error here surfaces naturally on the real launch.
    """
    subprocess.call(
        [
            *UVX_PREFIX,
            "--refresh-package",
            "sail",
            "--from",
            RUNTIME_SPEC,
            "python",
            "-c",
            "pass",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    if not pinned_available_offline():
        recover_stale_metadata()
    # Exec replaces this process with the server: stdin/stdout are inherited
    # untouched and there is no code after a session that could retry.
    os.execvpe(WARM_COMMAND[0], WARM_COMMAND, os.environ)
    return 1  # pragma: no cover - execv never returns


if __name__ == "__main__":
    raise SystemExit(main())
