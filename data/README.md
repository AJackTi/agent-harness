# Data Engineering & Quality Profile (`data`)

Orchestration profile for data pipelines (ETL/ELT), schema migrations, and data quality verification ([profile.json](profile.json)), inheriting the core policy from [../core/policy.json](../core/policy.json).

## Tooling & Verification Requirements

- **Primary tools**: `python3`, `sqlite3` (along with query/data quality tools such as `duckdb` or `dbt` depending on the consumer repository).
- **Suggested verification commands (`example_unverified`)**:
  - Data quality checks (primary key uniqueness, `NULL` ratios, freshness, and schema backward compatibility).
  - Idempotency checks for data ingestion and transformation steps when re-running on the same time partition.
- **Expected evidence**: actual exit codes of the repository-accepted data quality and schema tests, along with `scope` verification and `git diff --check`.

## Mandatory Escalation Rule to `quant`

> **IMPORTANT**: Any `data` task that computes, transforms, or aggregates data related to **PnL, funding, liquidation, margin, leverage, or risk** must **explicitly** select the [../quant/README.md](../quant/README.md) profile (`--profile quant`) and run with `--work-kind quant`. The `data` profile only provides supplementary data infrastructure and schema context and must never be used to run quantitative tasks under `--work-kind task`.
