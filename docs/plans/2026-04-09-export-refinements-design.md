# Export Refinements Design

## Date: 2026-04-09

## Overview

Two improvements to the enriched export feature:
1. Corrected data export uses original CSV column names instead of generic headers
2. HTML validation report format refinements based on real-world print usage

---

## Item 1: Original Column Names in Corrected Export

### Problem
Corrected data export always uses fixed headers (`patient_id`, `icd_code`, etc.) regardless of the user's original CSV headers. Users want recognisable column names matching their source system.

### Approach
- Client passes column mapping (from localStorage) alongside claims in the export request
- API inverts mapping (ICDGuard field → original CSV header) and uses those as column names
- Fallback to current generic headers when no mapping is available (auto-detected formats)

### Files
- `app/review/page.tsx` — include column mapping in corrected export request body
- `app/api/export/route.ts` — accept `columnMapping`, invert it, apply to `claimToRow` keys and `buildCsv` headers

---

## Item 2: Report Format Refinements

### Changes

1. **Compact summary section** — reduce header padding and stat card sizes so the header + stats don't consume a full printed page
2. **Darker borders** — change table/row border colour from `#CBD5E1` to `#64748B` for better print visibility
3. **Remove extra line under patient header** — remove `border-bottom:2px solid #E2E8F0` on patient group header div
4. **Print-safe status colours** — add `-webkit-print-color-adjust: exact; print-color-adjust: exact;` to `@media print` so status badge colours (green/red/orange) survive printing
5. **Original CSV line numbers** — use `claim.id` (1-based CSV row number) instead of `idx + 1` so filtered reports show the correct source line number
6. **Filename in report header** — display the validated filename in the report header area

### Files
- `lib/export-report.ts` — add `line_number` field to `ReportRow`, populate from `claim.id`
- `lib/report-html.ts` — CSS/template fixes (compact header, darker borders, remove patient header underline, print colours, line numbers, filename display)
- `app/api/export/route.ts` — pass `filename` to `buildReportHtml`
- `app/review/page.tsx` — pass `filename` in report export request body
