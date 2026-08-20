---
name: sail-pick-models
description: Use when the user asks to inspect, choose, configure, change, or reset the models Sail uses for delegated work. Manages one persistent default plus optional recon, implementation, and review overrides for new Sail delegations on this device. Also use for requests such as use GLM for implementation and DeepSeek for recon, make DeepSeek the default, show my Sail model settings, or restore Sail model defaults. Do not use for a one-call model override on an otherwise ordinary delegation.
---

# Sail Pick Models

Manage the saved worker-model preferences used by new Sail delegations. This
skill changes local settings only. It does not start paid work.

## Read the current settings

Call `sail_get_model_preferences` first. Use its `available_models` result as
the source of truth for accepted saved models and aliases. Do not guess a model
identifier or offer a model outside that curated list.

There is one default and three optional role overrides:

- `recon` for a Sail Swarm discovery round.
- `implementation` for writable delegated work.
- `review` for Sail Review and optional verification fanouts.

A role with no override inherits the default. The built-in default is DeepSeek
V4 Flash 0731, so a fresh installation uses it for every role.

## Apply the request

Call `sail_set_model_preferences` with only the fields the user asked to
change. Map the default to `default_model`, and map role requests to
`recon_model`, `implementation_model`, or `review_model`. Pass `inherit` for a
role when the user asks to clear its override or make it follow the default.

Natural model names are sufficient when they match an alias returned by the
read tool. Let the MCP tool canonicalize them. If a requested name is
ambiguous or unavailable, show the curated choices and ask the user to choose.

Call `sail_reset_model_preferences` only when the user explicitly asks to
restore all built-in defaults. Do not implement a reset by setting each field
individually.

## Report the result

Summarize the returned effective default and role models. State that the
settings persist on this device and affect new delegations. Active work and
resumed delegations keep the model resolved when they started. An explicit
`model` on a later delegation remains a one-call override and wins over these
settings.

Do not edit the settings file directly and do not call a delegation tool as a
test. The preference tool result is the verification.
