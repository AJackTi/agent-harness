# Dashboard Domain Profile (`dashboard`)

Orchestration profile for administrative and analytics dashboards ([profile.json](profile.json)), inheriting directly from [../frontend/README.md](../frontend/README.md) (`"extends": ["frontend"]`) and the core policy in [../core/policy.json](../core/policy.json).

## Key Extensions from `frontend`

Beyond the baseline `frontend` requirements (framework/package-manager independence and browser automation support), `dashboard` mandates verification across four additional areas:

1. **Table and Chart Data Integrity (`data`)**: Handle empty datasets, pagination, and consistent metric aggregation between tables and charts.
2. **Filter Synchronization (`filter`)**: Preserve filter state across URL query parameters and application state, avoiding race conditions when users rapidly change filters.
3. **Timezone Normalization (`timezone`)**: Display and query timestamps consistently between `UTC` and local timezones, especially across day and session boundaries.
4. **Role-Based Access Control (`RBAC`)**: Verify permission state and prevent sensitive data leakage rather than merely hiding UI buttons.

## Mandatory Escalation Rule to `quant`

> **IMPORTANT**: Any `dashboard` task involving calculating, aggregating, or reconciling **PnL, funding, liquidation, margin, or risk** must explicitly select the [../quant/README.md](../quant/README.md) profile (`--profile quant`) and run with `--work-kind quant`. The `dashboard` profile provides UI context only and must never be used to implicitly run quantitative tasks under `--work-kind task`.
