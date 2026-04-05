# User-Defined Import Format Mapper — Design

**Date:** 2026-04-05

## Goal

When a CSV doesn't match any known parser, show a column mapping UI so users can map their headers to ICDGuard fields. Save the mapping for automatic reuse on future uploads.

## Decisions

| Aspect | Decision |
|--------|----------|
| Trigger | Only for unknown formats (known parsers + auto-detect work as today) |
| UI | New mapper step between upload and validation |
| Display | Table of CSV headers → ICDGuard field dropdowns, with 3-5 row data preview |
| Required fields | Patient ID, Service Date, ICD Code, Tariff Code |
| Optional fields | Patient Name, DOB, Gender, Amount, Quantity, Provider |
| Storage | localStorage keyed by hash of sorted column headers |
| Reuse | Auto-match on next upload — if headers match saved mapping, apply silently |
| DB migration | localStorage → user-specific DB table when accounts are built |

## Validation During Mapping

- Required fields not yet mapped → "Save & Validate" button disabled, shows which fields still need mapping
- If a required field has no suitable column → warning: "This file has no [field] column — it cannot be validated"
- User can go back and upload a different file

## Flow

1. User uploads CSV on `/` (upload page)
2. `detectSourceSystem()` returns `'unknown'`
3. Mapper screen appears with column headers, dropdowns, and data preview
4. Button disabled until all 4 required fields are mapped
5. User maps columns, clicks "Save & Validate"
6. Mapping saved to localStorage: `icdguard-mappings` → `{ [headerHash]: mapping }`
7. File parsed using custom mapping → validation proceeds as normal
8. Next upload with same headers → mapping auto-applied, straight to validation

## Upload Page Changes

- Add "Auto-detect" as default source system option
- If unknown and no saved mapping → show mapper
- If unknown and saved mapping matches → apply silently, proceed to validation

## Styling Requirements

Must match ICDGuard design language exactly:
- Navy (#1a3a6b) for headers, primary buttons, and active states
- White cards on slate-50 background (bg-slate-50 page, bg-white card)
- Dark text on light backgrounds — never white on white
- Same rounded-lg cards, border-slate-200, shadow-sm patterns as upload/review pages
- Dropdowns styled like existing inputs (border-gray-300, rounded-lg, focus:ring-[#1a3a6b])
- Data preview table with alternating row colours (white/slate-50) for readability
- Required field indicators in red-500
- Warning/error states in amber/red matching existing validation colours
- Disabled button state: bg-gray-300, cursor-not-allowed
- Active button: bg-[#1a3a6b] text-white hover:bg-[#152e56]

## Out of Scope

- User accounts or DB persistence (future)
- Named/editable saved mappings (future — when user settings page exists)
- Known parser changes (GoodX, Elixir, Medinol, Healthbridge unchanged)
- Validation engine changes
- Review page changes
- Export flow changes
