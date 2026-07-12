---
name: sail-gpu-marketplace
description: Use when an agent needs to rent a preemptible (spot) GPU VM through Sail — allocate an H100, H200, or A100 node, wait for real CUDA readiness, connect over SSH, execute or transfer work, forward a port, release capacity, or recover a checkpointed training job after an interruption. The bundled connector handles verified TLS, per-allocation SSH keys, idempotent allocation requests, and cooperative reallocation. The training program still owns checkpoint creation and resume semantics.
---

# Sail GPU Marketplace

Use this skill when work running on Sail needs a dedicated GPU VM. The GPU is a
separate preemptible resource. Your controller allocates it, connects remotely,
and releases it when the work finishes.

The connector is `scripts/sail_gpu.py` beside this file. Resolve that file to an
absolute path before invoking it:

```bash
export SAIL_GPU_TOOL=/absolute/path/to/sail-gpu-marketplace/scripts/sail_gpu.py
export SAIL_API_KEY=...
export SAIL_GPU_ACCESS_HOST=...  # endpoint supplied during onboarding
```

Keep `SAIL_API_KEY` in the environment. Never pass it as a command-line flag,
write it into a remote shell command, or copy it onto the GPU VM. The connector
uses the local SSH private key only for SSH; allocation creation sends its
public half to Sail.

## What you can request (beta)

- **Accelerators** are `H100`, `H200`, or `A100-80GB`. Do not request anything
  else, and never silently substitute one for another.
- **`--gpu-count` is 1 to 8** (one node). Every allocation is a whole dedicated
  node regardless of the count, so asking for fewer GPUs does not get a smaller
  or cheaper machine in the beta.
- **One managed image and one node size.** There is no custom image or instance
  selection yet; do not pass image or size fields.
- **The fulfillment window is about 30 minutes.** Spot capacity is scarce, so an
  allocation can sit `pending` or `provisioning` for minutes before it fills, or
  end `unfulfillable`. That is a normal outcome — keep polling, do not give up
  early, and do not fall back to a different accelerator.
- **There are concurrency and spend ceilings** (a maximum number of active
  nodes, a maximum number of active GPUs, and a cumulative spend cap). On a
  create rejected with HTTP 429, act on the error `type` — do not blindly retry:
  - `quota_exceeded_error` (active node or GPU ceiling) — **release a finished
    allocation** to free headroom, then retry.
  - `spend_cap_exceeded_error` (cumulative spend) — releasing does **not**
    restore already-spent budget, so it won't help. **Stop, lower demand, or ask
    Sail to raise the cap.**
  Either way, never retry the same request in a tight loop.

## Preferred workflow

Use `run` for a cooperative, checkpointed job:

```bash
python "$SAIL_GPU_TOOL" run \
  --accelerator H100 \
  --gpu-count 8 \
  --checkpoint-uri "$CHECKPOINT_URI" \
  --command 'python train.py'
```

The remote command receives:

- `SAIL_CHECKPOINT_URI`: where it must periodically publish complete
  checkpoints.
- `SAIL_RESUME_FROM`: empty on the first attempt, then the checkpoint URI after
  an interrupted attempt.

The program must also watch `/run/sail/reclaim.json` and flush a final
checkpoint when that file appears. The connector can detect an interruption,
allocate a replacement, and set `SAIL_RESUME_FROM`; it cannot infer how an
arbitrary training program serializes or restores its state. Do not claim
managed resume until the real program has passed an interruption drill.

`run` releases a live allocation on success, command failure, or controller
error. It does not retry ordinary program failures. It reallocates only after
the allocation reports an interruption.

## Manual workflow

Allocate and wait for the desired state:

```bash
python "$SAIL_GPU_TOOL" allocate \
  --accelerator H100 \
  --gpu-count 8 \
  --checkpoint-uri "$CHECKPOINT_URI"
```

Each create carries an `Idempotency-Key`. The connector prints the key before
the request; reuse it with `--idempotency-key` only when recovering a create
whose response was lost. Do not reuse a key for a new run.

Use the returned allocation id for access:

```bash
python "$SAIL_GPU_TOOL" ssh ALLOCATION_ID
python "$SAIL_GPU_TOOL" exec ALLOCATION_ID -- nvidia-smi -L
python "$SAIL_GPU_TOOL" copy ALLOCATION_ID ./train.py gpu:/workspace/train.py
python "$SAIL_GPU_TOOL" copy ALLOCATION_ID gpu:/workspace/result.json ./result.json
python "$SAIL_GPU_TOOL" forward ALLOCATION_ID 8888 127.0.0.1:8888
```

Release in a `finally` path. Idle reclamation is not a substitute for cleanup:

```bash
python "$SAIL_GPU_TOOL" release ALLOCATION_ID
```

## Operating rules

- A `running` allocation means the VM exists. Use `run`, or retry SSH and CUDA,
  before declaring the GPU usable.
- Capacity is preemptible and may remain unavailable through the fulfillment
  window. Treat `unfulfillable` as a normal capacity outcome.
- Never silently change the requested accelerator or fall back to a different
  capacity class.
- Use SSH port forwarding for notebook or dashboard access. Do not expose a
  service directly from the VM.
- Store durable datasets and checkpoints outside the VM. Local disks disappear
  with the allocation.
- The VM has outbound HTTPS for installing dependencies, but stage large
  datasets in S3 and write every checkpoint to the checkpoint URI. Pulling big
  data over the internet is slower and costlier than reading it from S3.
- Record request-to-running, request-to-SSH, request-to-CUDA, checkpoint age,
  interruption count, and resume time for every beta run.
