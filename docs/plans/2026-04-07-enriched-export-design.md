# Enriched Export Design

## Problem
The current export outputs a flat file with generic column names and silently-applied corrections. Users don't upload this to their billing system — they use it as a reference while fixing their actual system. The export doesn't show what changed, what issues remain, or what to do next.

## Solution
Two export types, user's choice:

### 1. Corrected Data Export (improved current)
- Uses the user's **original column headers** (from mapper or detected parser)
- Corrections silently applied (same as today)
- Adds one column at end: **Status** (Valid / Needs Review / Rejected)
- Format respects original upload (CSV highlighted for CSV uploads, Excel for Excel)

### 2. Validation Report Export (new)
A correction worksheet — the user's to-do list.

**Columns:**
| Column | Content |
|--------|---------|
| Patient ID | Find the line in their system |
| Patient Name | Context |
| Service Date | Context |
| Status | Valid / Needs Review / Rejected |
| Issues Found | All issues (errors + warnings) with severity prefix, semicolon-separated |
| Changes Made | Per-line corrections, e.g. "ICD: R10 -> R10.1" — blank if none |
| Suggestions | Remaining unapplied suggestions |

**Behaviour:**
- Default: only lines with issues (rejected + needs_review)
- "Include valid lines" checkbox: adds clean lines with Status=Valid and empty issue columns
- Sorted by patient ID, then service date
- Excel format: row colouring (red=rejected, amber=needs_review, green=valid)

### UI Changes
Export area on review page becomes a small panel with:
- **Export Corrected Data** button
- **Export Validation Report** button
- Format toggle (CSV / Excel), highlighted to match original upload format
- "Include valid lines" checkbox (only visible when Validation Report selected)

### API Changes
`/api/export` route extended with:
- `type: 'corrected' | 'report'` parameter
- `includeValid: boolean` parameter (for report type)
- Report-building logic: computes changes by comparing corrections to original values
- Excel colour formatting for report type
