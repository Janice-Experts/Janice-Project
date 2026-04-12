# Summary Report Design

## Overview

Add a "Summary" report style alongside the existing "Detailed" report. The summary strips away warning explanations, severity icons, colour-coded badges, and suggestion details — producing a clean, print-friendly checklist a user can work through line by line.

## UI Change

Add a **Report Style** radio group to the export panel, above Report Type:

- **Summary** / **Detailed**

Report Type options remain the same for both styles:
- Errors only
- Needs review
- Errors and Review
- Changes only
- Full report

Format options remain the same: HTML, JSON.

## Summary Report Layout (HTML)

### Header
Report title, filename, generation date, total claims/patients. Plain text — no gradient banner.

### Summary Stats
Single line: "42 lines | 5 errors | 3 needs review | 34 valid | 8 corrected"

### Per-Patient Tables

Patient header: name, ID, service date.

| # | ICD Code | Tariff Code | Status | Action Needed |
|---|----------|-------------|--------|---------------|
| 3 | A00 → A00.1 | 0190 | Rejected | Change ICD to A00.1 |
| 4 | B34.9 | 0191 → 0192 | Needs Review | Change Tariff to 0192 |
| 7 | J06.9 | 0190 | Valid | |

- Old → New shown inline with arrow for changed codes
- Status as plain text (no coloured badges)
- Action Needed: plain text describing what to do, blank if nothing needed
- No warning/error icons, no severity, no suggestion stars
- Minimal borders, no row background colours — clean black & white, print-friendly

### Footer
Generation timestamp.

## JSON Format

Same ReportRow structure with a simplified `action_needed` string field replacing the separate `issues_found`, `changes_made`, `suggestions` fields.

## Technical Approach

1. Add `reportStyle` state (`'summary' | 'detailed'`) to review page export panel
2. Pass `reportStyle` through to `/api/export` endpoint
3. Create `buildSummaryReportHtml()` in new `lib/report-summary-html.ts`
4. `buildReportRows()` stays shared — filtering logic is the same, only rendering differs
5. Export API routes to detailed or summary HTML builder based on style param

## Files to Change

- `app/review/page.tsx` — add Report Style radio group, pass style to export
- `app/api/export/route.ts` — accept `reportStyle`, route to correct builder
- `lib/report-summary-html.ts` — new file, summary HTML builder
- `lib/export-report.ts` — add `action_needed` field to ReportRow for summary use
