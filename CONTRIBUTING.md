# Contributing

Thanks for your interest in improving Sail's skills.

## How this repo works

This repository is a **curated export**: the skills are developed and tested
against the Sail platform in an internal source-of-truth tree, and each release
here is a verbatim copy of that validated payload. Content only flows one way
(source → this repo), so changes cannot be merged here directly — anything
merged here would be overwritten by the next export.

## Proposing a change

- **Open an issue first** for bugs, inaccuracies, or confusing guidance in a
  skill. This is the fastest path: maintainers apply accepted fixes upstream
  and they land here in the next release.
- **Pull requests are welcome as concrete proposals**, but please expect them
  to be closed with a reference once the change is applied upstream, rather
  than merged directly. Crediting the proposal in the release notes is on us.
- **Product support** (accounts, API keys, dashboard questions) belongs at
  [sailresearch.com](https://sailresearch.com), not in this issue tracker.
- **Security concerns**: please contact Sail privately via
  [sailresearch.com](https://sailresearch.com) rather than filing a public
  issue.

## What makes a good skill change

The skills follow the [Agent Skills](https://agentskills.io) standard and a few
house rules: SKILL.md stays under 500 lines, examples are small and
self-contained, descriptions are mutually exclusive across skills, and
everything must be runnable by someone outside Sail with just an API key. If
your proposal fits those constraints, it has a good chance of being adopted.
