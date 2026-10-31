# Design Provenance & Conceptual References (`docs/PROVENANCE.md`)

This document records the architectural inspiration behind `ajackti-agent-harness` and defines its code ownership and integration boundaries.

## 1. Conceptual References

The design of `ajackti-agent-harness` draws organizational principles from two reference repositories:

1. **`repository-harness`**:
   - Keeping the root `AGENTS.md` concise as a navigation map (compact entrypoint).
   - Treating the repository as the single source of authority (repository as source of authority).
   - Progressive context discovery from `core` through `domain profile` definitions and `repo-context`.
   - Strictly distinguishing unverified candidate commands (`example_unverified`) from verification commands accepted by the consumer repository.
2. **`harness-engineering-demo`**:
   - Evidence-based completion backed by a verifiable proof pack (evidence-based completion / proof pack).
   - Clear separation between orchestration policy, task input data (task packet), and the output evidence directory located outside the workspace.

## 2. Independent Implementation & Strict Boundaries

- **Original Implementation**:
  - All source code ([../scripts/harness.py](../scripts/harness.py)), test suites ([../tests/test_harness.py](../tests/test_harness.py)), JSON schemas ([../harness.json](../harness.json), [../core/policy.json](../core/policy.json), `<domain>/profile.json`), and documentation in this repository were written from scratch for AJACKTI's personal needs.
  - This repository **does not copy source code** from `repository-harness` or `harness-engineering-demo`.
- **No Inherited Installer**:
  - `ajackti-agent-harness` **does not** inherit, use, or assume the installer of any reference project.
- **No Bundled Skills**:
  - Execution runners such as `antigravity-task-runner` and `antigravity-sol-quant-runner` are independent skills installed under `~/.agents/skills` on the user's machine.
  - [../scripts/harness.py](../scripts/harness.py) acts strictly as a thin adapter invoking `scripts/run_workflow.py` from the installed skill; it never vendors or rewrites the security gates of those runners here.
