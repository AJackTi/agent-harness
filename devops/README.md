# DevOps & Infrastructure Profile (`devops`)

Orchestration profile for Infrastructure as Code (IaC), containers, and CI/CD pipelines ([profile.json](profile.json)), inheriting the core policy from [../core/policy.json](../core/policy.json).

## Tooling & Verification Requirements

- **Primary tools**: `terraform`, `docker`, `kubectl` (project-optional), `shellcheck` (optional).
- **Suggested verification commands (`example_unverified`, `requires_consumer_acceptance=true` — pass each command via separate `--verify-cmd` flags; do not chain commands with shell operators or use unexpanded glob patterns)**:
  - `terraform fmt -check -recursive` (offline IaC formatting check)
  - `terraform validate` (offline IaC configuration validation)
  - `docker build --check .` (static Dockerfile validity check)
  - `shellcheck scripts/deploy.sh` (static check of a specific script file designated by the repository)
  - `python3 scripts/harness.py validate` (validate JSON configuration, profiles, templates, and Markdown links of the harness repository)
- **Verification scope note**: The commands above are `example_unverified` only and require explicit acceptance from the consumer repository owner; they do not assert that the tools are pre-installed on the machine and do not prove application runtime behavior.
- **Expected evidence**: actual exit codes of each repository-accepted static/offline verification command, along with `scope` verification and `git diff --check`.
- **Domain-specific risks**:
  - Strictly do not run `apply`, `deploy`, or `push` commands or modify live configs, endpoints, credentials, or safety gates without explicit user approval.
  - All checks within the harness must remain strictly at the static/offline validation level unless explicitly authorized by the repository owner.
