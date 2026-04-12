# Success Probability Score Design

## Overview

Add a per-line and per-claim probability score predicting the likelihood a medical scheme will pay the claim. The score reflects the current state of each line (after user corrections and accepted warnings).

## Scoring Model

Each line starts at **100%**. Each active validation issue applies a multiplier. Multiple issues compound (multiply together). The score never exceeds 100%.

Example: `ICD_UNSPECIFIED` (×0.60) + `DATE_STALE_CLAIM` (×0.60) = 100% × 0.60 × 0.60 = **36%**.

## Issue Multipliers

| Category | Code | Multiplier |
|---|---|---|
| Fatal | MISSING_ICDCODE, MISSING_TARIFFCODE, MISSING_PATIENTID, MISSING_SERVICEDATE | ×0.00 |
| Fatal | ICD_INVALID, TARIFF_INVALID, ICD_ECC_AS_PRIMARY | ×0.00 |
| Fatal | DATE_FUTURE_SERVICE, DATE_BEFORE_BIRTH | ×0.00 |
| High risk | DEMO_GENDER_MISMATCH | ×0.20 |
| High risk | DEMO_AGE_NEONATAL, DEMO_AGE_INFANT | ×0.25 |
| Medium risk | ICD_UNSPECIFIED | ×0.60 |
| Medium risk | TREATMENT_MISMATCH | ×0.60 |
| Medium risk | DUPLICATE_CLAIM | ×0.50 |
| Medium risk | DATE_STALE_CLAIM | ×0.60 |
| Low risk | ICD_MISSING_ECC | ×0.85 |
| Low risk | DEMO_AGE_PAEDIATRIC, DEMO_AGE_CHILD, DEMO_AGE_ADULT_ONLY | ×0.85 |
| Boost | PMB_CONDITION | ×1.05 |

## Accepted Warnings

When a user accepts/acknowledges warnings on a line, those warning issues are excluded from the score calculation. An accepted line with no remaining issues = 100%.

## Claim Score

The claim score (per patient + service date group) is the **lowest line score** in the group. One bad line drags the whole claim down.

## Batch Stats

Overall average of all line scores, shown in the KPI summary bar.

## Display

Percentage with colour coding:
- 90-100% — green
- 60-89% — amber
- 1-59% — red
- 0% — red, bold

### Where It Shows

- **ClaimCard** (`components/ClaimCard.tsx`) — per-line score near the status badge
- **ClaimGroupCard** (`components/ClaimGroupCard.tsx`) — claim score in group header alongside patient stats
- **KpiBar** (`components/KpiBar.tsx`) — batch average score as a new KPI card
- **Reports** — both detailed and summary report HTML include the score per line and per patient group

## Technical Approach

1. New `lib/probability.ts` with:
   - `ISSUE_MULTIPLIERS` map (code → multiplier)
   - `calcLineScore(issues, acceptedIds, claimId)` → number (0-100)
   - `calcClaimScore(lineScores)` → number (min of line scores)
2. Call `calcLineScore` during validation or at render time from existing issue data
3. Add score to ClaimCard, ClaimGroupCard, KpiBar display
4. Add score column to report builders (both detailed and summary)

## Files to Change

- Create: `lib/probability.ts` — scoring logic
- Modify: `components/ClaimCard.tsx` — show line score
- Modify: `components/ClaimGroupCard.tsx` — show claim score in header
- Modify: `components/KpiBar.tsx` — add batch average score card
- Modify: `lib/report-html.ts` — add score column to detailed report
- Modify: `lib/report-summary-html.ts` — add score column to summary report
- Modify: `lib/export-report.ts` — add `probability` field to ReportRow
