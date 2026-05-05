# Learned Tariff Substitutions — Design

**Date**: 2026-05-05
**Status**: Approved, pending implementation plan

## Goal

ICDGuard learns common tariff-code corrections (A → B) from accumulated user data and surfaces soft warnings on future uploads of `A`. The system gets smarter over time without users entering rules manually.

## Approach

- Mine the existing `claims.corrected_tariff_code` data — every accepted correction is already captured.
- Aggregate per `(original → corrected)` pair.
- Promote a pair to a "rule" when volume + dominance thresholds are met.
- Surface as a soft, acknowledgeable warning on future uploads of `original`.

## Data source

The `claims` table already stores both:
- `tariff_code` — what was uploaded
- `corrected_tariff_code` — final value after user correction

A **correction event** = a claim row where `corrected_tariff_code` is non-null AND `corrected_tariff_code != tariff_code`.

## New table: `tariff_substitution_rules`

Materialised aggregate. Updated eagerly on each correction.

| column | type | note |
|---|---|---|
| original | text | NOT NULL |
| corrected | text | NOT NULL |
| count | int | corrections of original → corrected |
| dismissed_count | int | times a user dismissed this suggestion (tracked, unused in v1) |
| last_seen | timestamptz | for future decay logic |

**PK**: `(original, corrected)`

`total_seen` (corrections of `original` to anything) is computed at read time:
```sql
SUM(count) OVER (PARTITION BY original)
```
The table will be small — sub-millisecond queries.

## Rule-firing thresholds

A rule fires when **both** are true:
- **Volume**: `count` ≥ 10
- **Dominance**: `count / total_seen` ≥ 0.70

These are starting values. Tunable once we see real data.

## Update strategy

When a claim row is saved with a tariff correction (whether via accepted suggestion, batch correction bar, or manual edit):
1. `UPSERT` increment `tariff_substitution_rules` for `(original, corrected)` — `count += 1`, `last_seen = now()`.

That's it. No batch job, no scheduling.

When a user dismisses a learned suggestion:
1. `UPDATE` `dismissed_count += 1` for the `(original, corrected)` row.

Dismissal data is collected for future use; v1 does not let dismissals weaken rules.

## Validator integration

New file: `lib/validators/learned.ts`. Runs after existing validators in the engine. For each line item with a `tariff_code`:

1. Query `tariff_substitution_rules` for rows where `original = tariff_code` and thresholds are met.
2. If a row qualifies, emit a soft warning issue:
   - `severity: 'info'` (new severity tier — distinct from `error` and `warning`)
   - `code: 'LEARNED_SUBSTITUTION'`
   - `suggested_value: corrected`
   - `message: 'Typically corrected to {corrected} ({count} of {total_seen} corrections, {dominance}%)'`
   - Acknowledgeable
   - **Does not affect probability score**

## UX

The existing card UX already supports issue display, suggestion application, and acknowledgement. The learned warning slots in alongside other issues with a distinct visual cue (e.g. lightbulb icon, neutral grey background) to signal "this is a community hint, not a defect".

User actions:
- **Apply suggestion** → tariff updated → counts as another correction (rule self-reinforces).
- **Dismiss** → `dismissed_count` increments. No further effect in v1.
- **Ignore** → claim still validates as before.

## Cold start

At launch: 0 rules. Empty state. The feature does nothing visible until the corrections data accumulates. Optional: seed manually with a handful of known strong patterns from domain knowledge.

## Out of scope for v1 (YAGNI)

- ICD substitution learning (separate feature, future)
- Conditional rules (`tariff + ICD → tariff`)
- Per-scheme rules (Discovery / Bonitas / GEMS)
- Per-practice / per-user rule scoping (requires auth)
- Decay / rule expiry
- Automatic rule application
- Dismissal-based rule weakening
- Admin UI for managing rules (DB query suffices initially)

## Open questions / future enhancements

- **Self-reinforcement risk**: if a learned suggestion is wrong, users will dismiss it. v1 doesn't act on dismissals — fine while volume is small, but should be revisited once usage data is meaningful.
- **Per-practice scoping**: when auth lands, learned rules can split into "global" (shared corpus) + "yours" (your practice's pattern). The schema will need a nullable `scope_user_id`.
- **ICD-conditional rules**: same machinery, but key on `(original_tariff, icd_code)` → `corrected_tariff`. Likely a v2 feature once tariff-only proves itself.

## Admin visibility

No UI in v1. A SQL query is enough to inspect the rules:

```sql
SELECT
  original,
  corrected,
  count,
  SUM(count) OVER (PARTITION BY original) AS total_seen,
  ROUND(count::numeric / SUM(count) OVER (PARTITION BY original) * 100, 1) AS dominance_pct,
  last_seen
FROM tariff_substitution_rules
ORDER BY count DESC;
```

A simple `/admin/learned-rules` page can be added later if needed.
