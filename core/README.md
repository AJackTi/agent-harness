# Core Harness Layer (`core/`)

The `core/` directory contains the foundational policy shared across all domain profiles in `ajackti-agent-harness`.

## Components

- [policy.json](policy.json): Declarative JSON definition of the external-first `agy` policy, the coordinator-owned `model_selection` contract (allowed `claude-opus-5-5-high` and `gemini-4-argon-high`, preferred Opus while available, unset/empty `AGY_MODEL` defaulting to Gemini, `--effort high`), worker validation, the `jev-1.13.0` pipeline, the `--max-reworks 2` ceiling and task-wide `retry_policy` ledger, protected boundaries, and the routing rules for `antigravity-task-runner` vs `antigravity-sol-quant-runner`. [../scripts/model_policy.py](../scripts/model_policy.py) validates these contracts only; it fetches no quota and implements no automatic selection, failover, or retry engine.
- [AGENTS.template.md](AGENTS.template.md): Concise `AGENTS.md` template for copying into consumer repositories. Unfilled placeholders are explicitly marked with `<UNRESOLVED:...>`.

## Composition Model

1. **Core Policy ([policy.json](policy.json))**: Invariant across all domains; no profile or consumer repository may add unsupported models, lower effort, disable `--no-resume-worker`, bypass `jev-1.13.0`, or reset the retry ledger.
2. **Domain Profile (`<domain>/profile.json`)**: Adds tool requirements (`tools`), candidate verification commands (`candidate_checks` in `example_unverified` status), expected evidence (`expected_evidence`), and domain-specific risks (`special_risks`).
3. **Repo Context ([../templates/repo-context.json](../templates/repo-context.json))**: Owned by the consumer repository; defines `workdir`, the list of owner-accepted verification commands (`accepted_verify_cmds`), and the allowed file scope (`scope`).

See also [../AGENTS.md](../AGENTS.md) and [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).
