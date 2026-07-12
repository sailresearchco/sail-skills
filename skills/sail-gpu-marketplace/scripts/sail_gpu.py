#!/usr/bin/env python3
"""Allocate and connect to a Sail GPU VM with no third-party dependencies."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

DEFAULT_API_URL = "https://api.sailresearch.com"
DEFAULT_SSH_USER = "ubuntu"
TERMINAL_STATES = {
    "released",
    "interrupted",
    "reclaimed_idle",
    "unfulfillable",
    "failed",
}
INTERRUPTED_STATES = {"interrupting", "interrupted"}


class GPUError(RuntimeError):
    pass


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def api_key() -> str:
    value = os.environ.get("SAIL_API_KEY", "").strip()
    if not value:
        raise GPUError("SAIL_API_KEY is required")
    return value


def access_address(value: str) -> tuple[str, int]:
    value = value.strip()
    if not value:
        raise GPUError("set SAIL_GPU_ACCESS_HOST to the GPU access endpoint")
    if ":" not in value:
        return value, 443
    host, raw_port = value.rsplit(":", 1)
    if not host:
        raise GPUError("GPU access endpoint host is empty")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise GPUError(f"invalid GPU access endpoint port: {raw_port!r}") from exc
    if port < 1 or port > 65535:
        raise GPUError(f"invalid GPU access endpoint port: {port}")
    return host, port


def api_request(
    base_url: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise GPUError(f"{method} {path} returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GPUError(f"{method} {path} failed: {exc.reason}") from exc
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise GPUError(f"{method} {path} returned invalid JSON") from exc


def public_key_for_identity(identity: Path) -> str:
    identity = identity.expanduser().resolve()
    public_path = Path(str(identity) + ".pub")
    if public_path.is_file():
        public_key = public_path.read_text(encoding="utf-8").strip()
    else:
        result = subprocess.run(
            ["ssh-keygen", "-y", "-f", str(identity)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise GPUError(
                f"could not derive a public key from {identity}: {result.stderr.strip()}"
            )
        public_key = result.stdout.strip()
    if "\n" in public_key or not public_key.startswith(("ssh-", "ecdsa-")):
        raise GPUError(f"{public_path} does not contain one OpenSSH public key")
    return public_key


def default_identity() -> Path:
    for candidate in (Path("~/.ssh/id_ed25519"), Path("~/.ssh/id_rsa")):
        expanded = candidate.expanduser()
        if expanded.is_file():
            return expanded
    raise GPUError("pass --identity or create ~/.ssh/id_ed25519")


def identity_path(raw: str) -> Path:
    identity = Path(raw).expanduser() if raw else default_identity()
    if not identity.is_file():
        raise GPUError(f"SSH private key not found: {identity}")
    return identity.resolve()


def new_idempotency_key() -> str:
    return f"gpu-{uuid.uuid4()}"


def create_allocation(
    base_url: str,
    *,
    accelerator: str,
    gpu_count: int,
    identity: Path,
    checkpoint_uri: str = "",
    resume_from: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    request_key = idempotency_key or new_idempotency_key()
    body: dict[str, Any] = {
        "accelerator": accelerator,
        "gpu_count": gpu_count,
        "ssh_public_key": public_key_for_identity(identity),
    }
    if checkpoint_uri:
        body["checkpoint_uri"] = checkpoint_uri
    if resume_from:
        body["resume_from"] = resume_from
    log(f"creating allocation with Idempotency-Key {request_key}")
    return api_request(
        base_url,
        "POST",
        "/v1/gpu-allocations",
        body,
        {"Idempotency-Key": request_key},
    )


def get_allocation(base_url: str, allocation_id: str) -> dict[str, Any]:
    return api_request(base_url, "GET", f"/v1/gpu-allocations/{allocation_id}")


def wait_for_state(
    base_url: str,
    allocation_id: str,
    wanted: set[str],
    timeout_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_state = ""
    while time.monotonic() < deadline:
        allocation = get_allocation(base_url, allocation_id)
        state = str(allocation.get("state", ""))
        if state != last_state:
            log(f"{allocation_id}: {state}")
            last_state = state
        if state in wanted:
            return allocation
        if state in TERMINAL_STATES:
            raise GPUError(
                f"{allocation_id} reached terminal state {state!r} while waiting for {sorted(wanted)}"
            )
        time.sleep(3)
    raise GPUError(
        f"timed out after {timeout_seconds}s waiting for {sorted(wanted)}; last state {last_state!r}"
    )


def release_allocation(
    base_url: str, allocation_id: str, *, wait: bool = True
) -> dict[str, Any]:
    allocation = api_request(base_url, "DELETE", f"/v1/gpu-allocations/{allocation_id}")
    if wait and allocation.get("state") != "released":
        return wait_for_state(base_url, allocation_id, {"released"}, 300)
    return allocation


def read_status_line(sock: socket.socket, limit: int = 4096) -> str:
    data = bytearray()
    while len(data) < limit:
        chunk = sock.recv(1)
        if not chunk:
            raise GPUError("GPU access endpoint closed during authorization")
        if chunk == b"\n":
            return data.decode(errors="replace")
        data.extend(chunk)
    raise GPUError("GPU access endpoint returned an overlong authorization response")


def open_proxy(access_host: str, allocation_id: str) -> ssl.SSLSocket:
    host, port = access_address(access_host)
    raw = socket.create_connection((host, port), timeout=10)
    try:
        tls = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
    except Exception:
        raw.close()
        raise
    tls.settimeout(15)
    tls.sendall(f"SAIL-GPU-CONNECT {allocation_id} {api_key()}\n".encode())
    status = read_status_line(tls)
    if status != "OK":
        tls.close()
        raise GPUError(f"GPU access authorization failed: {status}")
    tls.settimeout(None)
    return tls


def pump_proxy(access_host: str, allocation_id: str) -> None:
    sock = open_proxy(access_host, allocation_id)
    stop = threading.Event()

    def downstream() -> None:
        try:
            while not stop.is_set():
                data = sock.recv(65536)
                if not data:
                    return
                os.write(sys.stdout.fileno(), data)
        except OSError:
            return
        finally:
            stop.set()
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    reader = threading.Thread(target=downstream, daemon=True)
    reader.start()
    try:
        while not stop.is_set():
            data = os.read(sys.stdin.fileno(), 65536)
            if not data:
                break
            sock.sendall(data)
    except OSError:
        pass
    finally:
        stop.set()
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()
        reader.join(timeout=1)


def proxy_command(script: Path, access_host: str, allocation_id: str) -> str:
    return shlex.join(
        [
            sys.executable,
            str(script),
            "--access-host",
            access_host,
            "proxy",
            allocation_id,
        ]
    )


def ssh_base_command(
    script: Path,
    access_host: str,
    allocation_id: str,
    identity: Path,
    ssh_user: str,
) -> list[str]:
    return [
        "ssh",
        "-i",
        str(identity),
        "-o",
        "BatchMode=yes",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=3",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        f"HostKeyAlias={allocation_id}",
        "-o",
        f"ProxyCommand={proxy_command(script, access_host, allocation_id)}",
        f"{ssh_user}@gpu",
    ]


def remote_shell_command(command: str) -> str:
    return "bash -lc " + shlex.quote(command)


def run_remote(
    script: Path,
    access_host: str,
    allocation_id: str,
    identity: Path,
    ssh_user: str,
    command: str,
    *,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ssh_base_command(script, access_host, allocation_id, identity, ssh_user)
        + [remote_shell_command(command)],
        check=False,
        text=True,
        capture_output=capture_output,
    )


def run_remote_until_terminal(
    script: Path,
    access_host: str,
    allocation_id: str,
    identity: Path,
    ssh_user: str,
    command: str,
    base_url: str,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    process = subprocess.Popen(
        ssh_base_command(script, access_host, allocation_id, identity, ssh_user)
        + [remote_shell_command(command)],
        text=True,
    )
    allocation: dict[str, Any] = {"id": allocation_id, "state": ""}
    while process.poll() is None:
        try:
            allocation = get_allocation(base_url, allocation_id)
        except GPUError as exc:
            log(f"{allocation_id}: status poll failed; retrying while job runs: {exc}")
            time.sleep(3)
            continue
        if allocation.get("state") in TERMINAL_STATES:
            if process.poll() is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            break
        time.sleep(3)

    final_status_known = False
    for attempt in range(3):
        try:
            allocation = get_allocation(base_url, allocation_id)
            final_status_known = True
            break
        except GPUError as exc:
            log(f"{allocation_id}: final status poll failed: {exc}")
            if attempt < 2:
                time.sleep(3)
    if not final_status_known and allocation.get("state") not in (
        TERMINAL_STATES | {"interrupting"}
    ):
        allocation = {**allocation, "state": "unknown"}
    return (
        subprocess.CompletedProcess(process.args, process.returncode),
        allocation,
    )


def wait_for_gpu(
    script: Path,
    access_host: str,
    allocation_id: str,
    identity: Path,
    ssh_user: str,
    timeout_seconds: int,
) -> dict[str, float]:
    deadline = time.monotonic() + timeout_seconds
    ssh_started = time.monotonic()
    while time.monotonic() < deadline:
        result = run_remote(
            script,
            access_host,
            allocation_id,
            identity,
            ssh_user,
            "true",
            capture_output=True,
        )
        if result.returncode == 0:
            break
        time.sleep(3)
    else:
        raise GPUError(f"timed out waiting for SSH on {allocation_id}")
    ssh_ready = time.monotonic()

    check = (
        "nvidia-smi -L >/dev/null && "
        "/opt/pytorch/bin/python -c 'import torch; assert torch.cuda.is_available(); "
        "print(torch.cuda.device_count())'"
    )
    while time.monotonic() < deadline:
        result = run_remote(
            script,
            access_host,
            allocation_id,
            identity,
            ssh_user,
            check,
            capture_output=True,
        )
        if result.returncode == 0:
            cuda_ready = time.monotonic()
            return {
                "ssh_wait_seconds": round(ssh_ready - ssh_started, 3),
                "cuda_wait_seconds": round(cuda_ready - ssh_ready, 3),
            }
        time.sleep(5)
    raise GPUError(f"timed out waiting for CUDA on {allocation_id}")


def allocation_after_disconnect(
    base_url: str, allocation_id: str, timeout_seconds: int = 30
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    allocation = get_allocation(base_url, allocation_id)
    while allocation.get("state") == "running" and time.monotonic() < deadline:
        time.sleep(3)
        allocation = get_allocation(base_url, allocation_id)
    if allocation.get("state") == "interrupting":
        return wait_for_state(
            base_url, allocation_id, {"interrupted", "reclaimed_idle", "released"}, 300
        )
    return allocation


def run_resumable(args: argparse.Namespace, script: Path) -> dict[str, Any]:
    if not args.checkpoint_uri:
        raise GPUError("run requires --checkpoint-uri")
    identity = identity_path(args.identity)
    resume_from = args.resume_from
    attempts: list[dict[str, Any]] = []

    for attempt in range(args.max_resumes + 1):
        created_at = time.monotonic()
        allocation = create_allocation(
            args.api,
            accelerator=args.accelerator,
            gpu_count=args.gpu_count,
            identity=identity,
            checkpoint_uri=args.checkpoint_uri,
            resume_from=resume_from,
        )
        allocation_id = str(allocation["id"])
        terminal = False
        cleanup_safe = True
        try:
            wait_for_state(args.api, allocation_id, {"running"}, args.timeout)
            running_at = time.monotonic()
            ready = wait_for_gpu(
                script,
                args.access_host,
                allocation_id,
                identity,
                args.ssh_user,
                args.ssh_timeout,
            )
            cuda_at = time.monotonic()
            setup = (
                "export PATH=/opt/pytorch/bin:$PATH; "
                f"export SAIL_CHECKPOINT_URI={shlex.quote(args.checkpoint_uri)}; "
                f"export SAIL_RESUME_FROM={shlex.quote(resume_from)}; "
            )
            result, allocation = run_remote_until_terminal(
                script,
                args.access_host,
                allocation_id,
                identity,
                args.ssh_user,
                setup + args.command,
                args.api,
            )
            if allocation.get("state") == "interrupting":
                allocation = wait_for_state(
                    args.api,
                    allocation_id,
                    {"interrupted", "reclaimed_idle", "released"},
                    300,
                )
            elif result.returncode != 0 and allocation.get("state") == "running":
                allocation = allocation_after_disconnect(args.api, allocation_id)
            state = str(allocation.get("state", ""))
            attempts.append(
                {
                    "allocation_id": allocation_id,
                    "state": state,
                    "command_exit_code": result.returncode,
                    "running_seconds": round(running_at - created_at, 3),
                    "cuda_ready_seconds": round(cuda_at - created_at, 3),
                    **ready,
                }
            )
            if state == "unknown":
                cleanup_safe = False
                raise GPUError(
                    f"allocation state unavailable after remote command exited: {allocation_id}"
                )
            if state in INTERRUPTED_STATES or state == "interrupted":
                terminal = state in TERMINAL_STATES
                if attempt >= args.max_resumes:
                    raise GPUError("resume limit reached after interruption")
                resume_from = args.checkpoint_uri
                log(f"{allocation_id} was interrupted; requesting a replacement")
                continue
            if result.returncode != 0:
                raise GPUError(
                    f"remote command exited {result.returncode} while allocation state was {state!r}"
                )
            release_allocation(args.api, allocation_id)
            terminal = True
            return {"status": "completed", "attempts": attempts}
        finally:
            if not terminal and cleanup_safe:
                try:
                    current = get_allocation(args.api, allocation_id)
                    if current.get("state") not in TERMINAL_STATES:
                        release_allocation(args.api, allocation_id)
                except GPUError as exc:
                    log(f"cleanup failed for {allocation_id}: {exc}")
    raise GPUError("unreachable resume-loop exit")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api", default=os.environ.get("SAIL_API_URL", DEFAULT_API_URL)
    )
    parser.add_argument(
        "--access-host", default=os.environ.get("SAIL_GPU_ACCESS_HOST", "")
    )
    parser.add_argument(
        "--ssh-user", default=os.environ.get("SAIL_GPU_SSH_USER", DEFAULT_SSH_USER)
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)

    allocate = subparsers.add_parser("allocate")
    allocate.add_argument("--accelerator", default="H100")
    allocate.add_argument("--gpu-count", type=int, default=8)
    allocate.add_argument("--identity", default="")
    allocate.add_argument("--checkpoint-uri", default="")
    allocate.add_argument("--resume-from", default="")
    allocate.add_argument("--idempotency-key", default="")
    allocate.add_argument("--timeout", type=int, default=1800)

    get = subparsers.add_parser("get")
    get.add_argument("allocation_id")

    release = subparsers.add_parser("release")
    release.add_argument("allocation_id")
    release.add_argument("--no-wait", action="store_true")

    proxy = subparsers.add_parser("proxy")
    proxy.add_argument("allocation_id")

    ssh = subparsers.add_parser("ssh")
    ssh.add_argument("allocation_id")
    ssh.add_argument("--identity", default="")
    ssh.add_argument("ssh_args", nargs=argparse.REMAINDER)

    execute = subparsers.add_parser("exec")
    execute.add_argument("allocation_id")
    execute.add_argument("--identity", default="")
    execute.add_argument("command", nargs=argparse.REMAINDER)

    copy = subparsers.add_parser("copy")
    copy.add_argument("allocation_id")
    copy.add_argument("source")
    copy.add_argument("destination")
    copy.add_argument("--identity", default="")

    forward = subparsers.add_parser("forward")
    forward.add_argument("allocation_id")
    forward.add_argument("local_port", type=int)
    forward.add_argument("remote")
    forward.add_argument("--identity", default="")

    run = subparsers.add_parser("run")
    run.add_argument("--accelerator", default="H100")
    run.add_argument("--gpu-count", type=int, default=8)
    run.add_argument("--identity", default="")
    run.add_argument("--checkpoint-uri", required=True)
    run.add_argument("--resume-from", default="")
    run.add_argument("--timeout", type=int, default=1800)
    run.add_argument("--ssh-timeout", type=int, default=600)
    run.add_argument("--max-resumes", type=int, default=3)
    run.add_argument("--command", required=True)
    return parser


def strip_separator(values: list[str]) -> list[str]:
    return values[1:] if values[:1] == ["--"] else values


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    script = Path(__file__).resolve()

    if args.operation == "allocate":
        identity = identity_path(args.identity)
        started = time.monotonic()
        allocation = create_allocation(
            args.api,
            accelerator=args.accelerator,
            gpu_count=args.gpu_count,
            identity=identity,
            checkpoint_uri=args.checkpoint_uri,
            resume_from=args.resume_from,
            idempotency_key=args.idempotency_key,
        )
        allocation = wait_for_state(
            args.api, str(allocation["id"]), {"running"}, args.timeout
        )
        allocation["running_seconds"] = round(time.monotonic() - started, 3)
        print(json.dumps(allocation, indent=2))
        return 0
    if args.operation == "get":
        print(json.dumps(get_allocation(args.api, args.allocation_id), indent=2))
        return 0
    if args.operation == "release":
        print(
            json.dumps(
                release_allocation(args.api, args.allocation_id, wait=not args.no_wait),
                indent=2,
            )
        )
        return 0
    if args.operation == "proxy":
        pump_proxy(args.access_host, args.allocation_id)
        return 0

    if args.operation == "run":
        if not args.access_host:
            raise GPUError("set SAIL_GPU_ACCESS_HOST to the GPU access endpoint")
        print(json.dumps(run_resumable(args, script), indent=2))
        return 0

    identity = identity_path(args.identity)
    if not args.access_host:
        raise GPUError("set SAIL_GPU_ACCESS_HOST to the GPU access endpoint")
    base = ssh_base_command(
        script,
        args.access_host,
        args.allocation_id,
        identity,
        args.ssh_user,
    )
    if args.operation == "ssh":
        return subprocess.call(base + strip_separator(args.ssh_args))
    if args.operation == "exec":
        command = strip_separator(args.command)
        if not command:
            raise GPUError("exec requires a command after --")
        return subprocess.call(base + [remote_shell_command(shlex.join(command))])
    if args.operation == "copy":
        remote = f"{args.ssh_user}@gpu:"
        source = (
            remote + args.source[4:] if args.source.startswith("gpu:") else args.source
        )
        destination = (
            remote + args.destination[4:]
            if args.destination.startswith("gpu:")
            else args.destination
        )
        scp = [
            "scp",
            "-i",
            str(identity),
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            f"HostKeyAlias={args.allocation_id}",
            "-o",
            f"ProxyCommand={proxy_command(script, args.access_host, args.allocation_id)}",
            source,
            destination,
        ]
        return subprocess.call(scp)
    if args.operation == "forward":
        return subprocess.call(
            base[:-1] + ["-N", "-L", f"{args.local_port}:{args.remote}", base[-1]]
        )
    raise GPUError(f"unsupported operation: {args.operation}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GPUError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except KeyboardInterrupt:
        raise SystemExit(130)
