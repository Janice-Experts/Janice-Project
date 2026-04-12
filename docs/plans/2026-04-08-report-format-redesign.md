# Report Format Redesign

## Problem
The current card-based HTML report layout spaces claims out so much that changes are hard to spot. Users work through the report patient by patient, making manual corrections in their billing system. Changes and required actions need to be immediately visible.

## Solution
Replace the card-per-claim layout with a **table-per-patient** layout. Keep the header, summary stats, and patient grouping. Each patient section has a compact table where one row = one claim line.

## Table Columns
| Column | Content |
|--------|---------|
| # | Line number within patient |
| Service Date | Date of service |
| ICD Code | Original code; if corrected shows `old → new` inline |
| Tariff Code | Original code; if corrected shows `old → new` inline |
| Status | Colour-coded badge (Rejected / Needs Review / Valid) |
| Issues | Errors and warnings, each on own line with severity icon |
| Action Required | Changes made + unapplied suggestions — the user's to-do |

## Row Styling
- Rejected: light red background (#FFF5F5, border #FCA5A5)
- Needs Review: light amber background (#FFFBEB, border #FCD34D)
- Valid: light green background (#F0FDF4, border #6EE7B7)

## Data Changes
`ReportRow` needs two new fields to support inline old→new display:
- `icd_original`: the pre-correction ICD code (blank if no change)
- `tariff_original`: the pre-correction tariff code (blank if no change)

The existing `changes_made` and `suggestions` fields merge into the Action Required column.

## Scope
- Only `lib/report-html.ts` layout changes (replace card functions with table functions)
- `lib/export-report.ts` gains `icd_original` and `tariff_original` fields on ReportRow
- No changes to CSV/XLSX/JSON export formats
- No changes to the review page UI or export panel
