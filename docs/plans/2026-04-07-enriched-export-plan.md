# Enriched Export Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "Validation Report" export option alongside the existing corrected-data export, and improve the corrected-data export to use original column names.

**Architecture:** Extend `/api/export` with a `type` param (`corrected` | `report`). Report-building logic lives in a new `lib/export-report.ts` helper. The review page export UI becomes a small panel with two export buttons, a format toggle, and an "include valid lines" checkbox. `acceptedIds` are passed to the API so the report can compute effective status.

**Tech Stack:** Next.js API route, `xlsx` library (already installed), Tailwind CSS for UI.

---

### Task 1: Add report row builder in `lib/export-report.ts`

**Files:**
- Create: `ICDGuard/lib/export-report.ts`

**Step 1: Create the report row builder**

This module takes a `ValidatedClaim[]`, `acceptedIds: string[]`, and `includeValid: boolean`, and returns report rows.

```typescript
import { ValidatedClaim, ClaimStatus } from '@/lib/types';

const ACKNOWLEDGEABLE_CODES = new Set(['PMB_CONDITION', 'ICD_UNSPECIFIED']);

interface ReportRow {
  patient_id: string;
  patient_name: string;
  service_date: string;
  icd_code: string;
  tariff_code: string;
  status: string;
  issues_found: string;
  changes_made: string;
  suggestions: string;
}

function effectiveStatus(claim: ValidatedClaim, acceptedIds: Set<string>): ClaimStatus {
  if (!acceptedIds.has(claim.id)) return claim.result.status;
  const hasNonAcknowledgeable = claim.result.issues.some(
    (i) => !ACKNOWLEDGEABLE_CODES.has(i.code)
  );
  return hasNonAcknowledgeable ? claim.result.status : 'valid';
}

function formatStatus(status: ClaimStatus): string {
  if (status === 'valid') return 'Valid';
  if (status === 'needs_review') return 'Needs Review';
  return 'Rejected';
}

function buildChanges(claim: ValidatedClaim): string {
  const changes: string[] = [];
  const fieldLabels: Record<string, string> = {
    icdCode: 'ICD',
    tariffCode: 'Tariff',
    treatmentCode: 'Treatment',
  };
  for (const [field, newValue] of Object.entries(claim.corrections)) {
    if (!newValue) continue;
    const label = fieldLabels[field] ?? field;
    const original = (claim as any)[field] ?? claim.raw[field] ?? '';
    if (original && original !== newValue) {
      changes.push(`${label}: ${original} → ${newValue}`);
    }
  }
  return changes.join('; ');
}

function buildIssues(claim: ValidatedClaim): string {
  return claim.result.issues
    .map((i) => {
      const severity = i.severity === 'error' ? 'ERROR' : 'WARNING';
      return `${severity}: ${i.message}`;
    })
    .join('; ');
}

function buildSuggestions(claim: ValidatedClaim): string {
  return claim.result.issues
    .filter((i) => i.suggestion && !claim.corrections[i.field])
    .map((i) => i.suggestion)
    .join('; ');
}

export function buildReportRows(
  claims: ValidatedClaim[],
  acceptedIdsList: string[],
  includeValid: boolean
): ReportRow[] {
  const accepted = new Set(acceptedIdsList);

  // Sort by patient ID, then service date
  const sorted = [...claims].sort((a, b) => {
    const pidCmp = (a.patientId ?? '').localeCompare(b.patientId ?? '');
    if (pidCmp !== 0) return pidCmp;
    return (a.serviceDate ?? '').localeCompare(b.serviceDate ?? '');
  });

  return sorted
    .filter((c) => {
      const status = effectiveStatus(c, accepted);
      return includeValid || status !== 'valid';
    })
    .map((c) => ({
      patient_id: c.patientId ?? '',
      patient_name: c.patientName ?? '',
      service_date: c.serviceDate ?? '',
      icd_code: c.corrections['icdCode'] ?? c.icdCode ?? '',
      tariff_code: c.corrections['tariffCode'] ?? c.tariffCode ?? '',
      status: formatStatus(effectiveStatus(c, accepted)),
      issues_found: buildIssues(c),
      changes_made: buildChanges(c),
      suggestions: buildSuggestions(c),
    }));
}
```

**Step 2: Commit**

```bash
git add ICDGuard/lib/export-report.ts
git commit -m "feat: add validation report row builder"
```

---

### Task 2: Extend `/api/export` route to handle report type

**Files:**
- Modify: `ICDGuard/app/api/export/route.ts`

**Step 1: Add report export path**

Import `buildReportRows` and handle `type === 'report'`. The request body gains: `type: 'corrected' | 'report'`, `acceptedIds: string[]`, `includeValid: boolean`.

For the report CSV path, use the report row headers. For the report XLSX path, add row colouring: red for Rejected, amber for Needs Review, green for Valid.

Add after the existing `format === 'xlsx'` block (before the "Unsupported format" return):

```typescript
// At top of POST handler, extract new params:
const type: string = body.type ?? 'corrected';
const acceptedIds: string[] = body.acceptedIds ?? [];
const includeValid: boolean = body.includeValid ?? false;

// New branch: if type === 'report', build report rows instead
```

For XLSX report, use `xlsx` cell styling for row colours:
- Iterate rows after creating the sheet
- Set fill colour based on status column value

**Step 2: Commit**

```bash
git add ICDGuard/app/api/export/route.ts
git commit -m "feat: extend export API with validation report type"
```

---

### Task 3: Update review page export UI

**Files:**
- Modify: `ICDGuard/app/review/page.tsx:112-230`

**Step 1: Replace export buttons with export panel**

Replace the two export buttons with a panel containing:
- "Export Corrected Data" button — calls `handleExport('corrected')`
- "Export Validation Report" button — calls `handleExport('report')`
- Format toggle (CSV / Excel) — default highlighted based on original filename extension
- "Include valid lines" checkbox — only visible when report is being exported (can use a small state flag or show inline)

**Step 2: Update `handleExport` function**

Change signature to accept `type: 'corrected' | 'report'`. The format (csv/xlsx) comes from a state variable. Pass `acceptedIds`, `includeValid`, and `type` in the POST body.

```typescript
const [exportFormat, setExportFormat] = useState<'csv' | 'xlsx'>(() =>
  summary.filename.toLowerCase().endsWith('.xlsx') || summary.filename.toLowerCase().endsWith('.xls')
    ? 'xlsx' : 'csv'
);
const [includeValid, setIncludeValid] = useState(false);

async function handleExport(type: 'corrected' | 'report') {
  setExporting(true);
  try {
    const res = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        claims,
        format: exportFormat,
        type,
        acceptedIds: Array.from(acceptedIds),
        includeValid,
      }),
    });
    // ... rest of download logic stays the same
    // Update suggested filename:
    const suffix = type === 'report' ? '-report' : '-corrected';
    const base = summary.filename.replace(/\.[^.]+$/, '');
    const suggestedName = `${base}${suffix}.${exportFormat}`;
    // ... existing download logic
  } finally {
    setExporting(false);
  }
}
```

**Step 3: Build the export panel UI**

Layout: a row with format toggle on left, two export buttons on right, checkbox below when relevant.

**Step 4: Commit**

```bash
git add ICDGuard/app/review/page.tsx
git commit -m "feat: add export panel with validation report option"
```

---

### Task 4: Improve corrected-data export to use original column names

**Files:**
- Modify: `ICDGuard/app/api/validate/route.ts:106` — include `originalHeaders` in response
- Modify: `ICDGuard/app/review/page.tsx` — pass `originalHeaders` through to export
- Modify: `ICDGuard/app/api/export/route.ts` — use original headers for corrected export

**Step 1: Pass original headers from validate API**

In the validate route, after parsing, extract the CSV headers from the first line of content and include them in the response:

```typescript
const originalHeaders = content.split(/\r?\n/)[0]
  .split(',')
  .map((h) => h.trim().replace(/"/g, ''));

return NextResponse.json({
  claims: validated,
  summary: summaryWithId,
  sourceSystem,
  warnings,
  originalHeaders,
});
```

**Step 2: Store and pass through in review page**

Add `originalHeaders` to the `ReviewData` interface and include it in the export POST body.

**Step 3: Use original headers in corrected export**

In the export route, when `type === 'corrected'` and `originalHeaders` is provided, map ICDGuard field names back to the original column names using a reverse lookup.

**Step 4: Commit**

```bash
git add ICDGuard/app/api/validate/route.ts ICDGuard/app/review/page.tsx ICDGuard/app/api/export/route.ts
git commit -m "feat: use original column names in corrected data export"
```

---

### Task 5: Manual testing pass

**Steps:**
1. Upload a CSV file → verify corrected export uses original column names
2. Upload an XLSX file → verify format toggle defaults to Excel
3. Export validation report with "include valid lines" off → verify only issue lines appear
4. Export validation report with "include valid lines" on → verify all lines appear
5. Export XLSX report → verify row colouring (red/amber/green)
6. Verify changes made column shows corrections accurately
7. Verify suggestions column shows unapplied suggestions
