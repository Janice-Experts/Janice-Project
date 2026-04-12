# Export Refinements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Use original CSV column names in corrected data exports and fix six HTML report format issues for better print usability.

**Architecture:** Client-side passes column mapping and filename to the export API. API inverts the mapping for column headers. Report HTML template gets targeted CSS and structure fixes.

**Tech Stack:** Next.js API routes, TypeScript, inline HTML/CSS report generation

---

### Task 1: Add `line_number` to ReportRow and populate from claim.id

**Files:**
- Modify: `ICDGuard/lib/export-report.ts:6-17` (ReportRow interface)
- Modify: `ICDGuard/lib/export-report.ts:94-110` (buildReportRows loop)

**Step 1: Add `line_number` field to the `ReportRow` interface**

In `lib/export-report.ts`, add `line_number` to the interface:

```typescript
export interface ReportRow {
  line_number: number;  // ← ADD THIS LINE
  patient_id: string;
  patient_name: string;
  // ... rest unchanged
}
```

**Step 2: Populate `line_number` from `claim.id` in `buildReportRows`**

In the `rows.push({...})` block (~line 99), add:

```typescript
rows.push({
  line_number: parseInt(claim.id, 10),  // ← ADD THIS LINE
  patient_id: claim.patientId ?? '',
  // ... rest unchanged
});
```

**Step 3: Commit**

```bash
git add ICDGuard/lib/export-report.ts
git commit -m "feat: add line_number to ReportRow from claim.id"
```

---

### Task 2: Report HTML — compact summary, darker borders, remove patient header line

**Files:**
- Modify: `ICDGuard/lib/report-html.ts`

**Step 1: Compact the header section**

In `buildReportHtml` (~line 198), reduce the header padding from `32px 40px` to `16px 40px`:

```typescript
// BEFORE:
<div style="background:linear-gradient(135deg, #1A3A6B 0%, #2563EB 100%);padding:32px 40px;color:white;">

// AFTER:
<div style="background:linear-gradient(135deg, #1A3A6B 0%, #2563EB 100%);padding:16px 40px;color:white;">
```

**Step 2: Compact the stat cards**

In `statCard` function (~line 67), reduce padding from `16px 20px` to `10px 16px` and font size from `1.75rem` to `1.25rem`:

```typescript
// BEFORE:
function statCard(label: string, value: number, color: string, bgColor: string): string {
  return `<div style="flex:1;min-width:120px;background:${bgColor};border-radius:10px;padding:16px 20px;">
    <div style="font-size:1.75rem;font-weight:700;color:${color};">${value}</div>
    <div style="font-size:0.8rem;color:#64748B;margin-top:2px;">${label}</div>
  </div>`;
}

// AFTER:
function statCard(label: string, value: number, color: string, bgColor: string): string {
  return `<div style="flex:1;min-width:100px;background:${bgColor};border-radius:10px;padding:10px 16px;">
    <div style="font-size:1.25rem;font-weight:700;color:${color};">${value}</div>
    <div style="font-size:0.75rem;color:#64748B;margin-top:2px;">${label}</div>
  </div>`;
}
```

Also reduce the summary container padding and margin. Change the summary section (~line 216):

```typescript
// BEFORE:
<div style="max-width:1200px;margin:-20px auto 0;padding:0 40px;">
  <div style="background:white;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);padding:24px;display:flex;gap:12px;flex-wrap:wrap;">

// AFTER:
<div style="max-width:1200px;margin:-10px auto 0;padding:0 40px;">
  <div style="background:white;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);padding:14px 24px;display:flex;gap:10px;flex-wrap:wrap;">
```

**Step 3: Darken all table borders**

Find-and-replace all occurrences of `#CBD5E1` with `#64748B` in `report-html.ts`. This affects:
- `codeCell` function (~line 74-76)
- `actionCell` function (~line 91)
- `issuesCell` function (~line 100-102)
- `claimRow` function (~line 110)
- `patientTable` thead (~line 150-156)

**Step 4: Remove the extra border-bottom on the patient header**

In the `patientTable` function (~line 130), remove `border-bottom:2px solid #E2E8F0;` from the patient header div:

```typescript
// BEFORE:
<div style="display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid #E2E8F0;padding-bottom:8px;margin-bottom:12px;">

// AFTER:
<div style="display:flex;justify-content:space-between;align-items:baseline;padding-bottom:8px;margin-bottom:12px;">
```

**Step 5: Commit**

```bash
git add ICDGuard/lib/report-html.ts
git commit -m "fix: compact summary, darken borders, remove patient header line"
```

---

### Task 3: Report HTML — print-safe status colours and original line numbers

**Files:**
- Modify: `ICDGuard/lib/report-html.ts`

**Step 1: Add print colour preservation to the `@media print` block**

In the `<style>` section (~line 187-192), add `print-color-adjust` rules:

```css
@media print {
  body { background: white; }
  .no-print { display: none !important; }
  .page-break { page-break-before: always; }
  @page { size: A4 landscape; margin: 1.5cm; }
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}
```

**Step 2: Use `line_number` instead of `idx + 1` in `claimRow`**

In the `claimRow` function (~line 105), change the signature and the line number cell:

```typescript
// BEFORE:
function claimRow(r: ReportRow, idx: number): string {

// AFTER:
function claimRow(r: ReportRow): string {
```

And the line number `<td>`:

```typescript
// BEFORE:
<td style="padding:6px 10px;border:1.5px solid #64748B;text-align:center;font-size:0.75rem;color:#94A3B8;font-weight:600;">${idx + 1}</td>

// AFTER:
<td style="padding:6px 10px;border:1.5px solid #64748B;text-align:center;font-size:0.75rem;color:#94A3B8;font-weight:600;">${r.line_number}</td>
```

**Step 3: Update the `.map()` call in `patientTable`**

In `patientTable` (~line 160), remove the index parameter:

```typescript
// BEFORE:
${group.rows.map((r, i) => claimRow(r, i)).join('')}

// AFTER:
${group.rows.map((r) => claimRow(r)).join('')}
```

**Step 4: Commit**

```bash
git add ICDGuard/lib/report-html.ts
git commit -m "fix: print-safe status colours and original CSV line numbers"
```

---

### Task 4: Add filename to report header

**Files:**
- Modify: `ICDGuard/lib/report-html.ts:166` (function signature)
- Modify: `ICDGuard/lib/report-html.ts:198-212` (header HTML)
- Modify: `ICDGuard/app/api/export/route.ts:47` (pass filename)
- Modify: `ICDGuard/app/review/page.tsx:199-226` (send filename in request)

**Step 1: Update `buildReportHtml` signature to accept filename**

```typescript
// BEFORE:
export function buildReportHtml(rows: ReportRow[], rType: ReportType): string {

// AFTER:
export function buildReportHtml(rows: ReportRow[], rType: ReportType, filename?: string): string {
```

**Step 2: Add filename to the header HTML**

After the subtitle line (~line 204), add the filename:

```typescript
// BEFORE:
<p style="font-size:0.85rem;opacity:0.8;">${subtitle} &mdash; ${date}</p>

// AFTER:
<p style="font-size:0.85rem;opacity:0.8;">${subtitle} &mdash; ${date}</p>
${filename ? `<p style="font-size:0.8rem;opacity:0.6;margin-top:2px;">File: ${esc(filename)}</p>` : ''}
```

**Step 3: Update the export API to pass filename**

In `app/api/export/route.ts`, extract filename from the request body (~line 8-13):

```typescript
const body = await req.json();
const claims: ValidatedClaim[] = body.claims;
const format: string = body.format ?? 'csv';
const type: 'corrected' | 'report' = body.type ?? 'corrected';
const acceptedIds: string[] = body.acceptedIds ?? [];
const reportType: ReportType = body.reportType ?? 'errors_review';
const filename: string | undefined = body.filename;  // ← ADD
```

Then pass it to `buildReportHtml` (~line 47):

```typescript
// BEFORE:
const html = buildReportHtml(reportRows, reportType);

// AFTER:
const html = buildReportHtml(reportRows, reportType, filename);
```

**Step 4: Send filename from the review page**

In `app/review/page.tsx` `handleGenerateReport` (~line 204), add filename to the request body:

```typescript
// BEFORE:
body: JSON.stringify({
  claims,
  format: reportFormat,
  type: 'report',
  reportType,
  acceptedIds: Array.from(acceptedIds),
}),

// AFTER:
body: JSON.stringify({
  claims,
  format: reportFormat,
  type: 'report',
  reportType,
  acceptedIds: Array.from(acceptedIds),
  filename: summary.filename,
}),
```

**Step 5: Commit**

```bash
git add ICDGuard/lib/report-html.ts ICDGuard/app/api/export/route.ts ICDGuard/app/review/page.tsx
git commit -m "feat: show validated filename in report header"
```

---

### Task 5: Original column names in corrected data export

**Files:**
- Modify: `ICDGuard/app/review/page.tsx:181-197` (handleExport — send mapping)
- Modify: `ICDGuard/app/api/export/route.ts:59-86` (corrected data export — accept and use mapping)

**Step 1: Send column mapping from review page**

In `app/review/page.tsx`, import `findSavedMapping` and add mapping retrieval. At top of file, add import:

```typescript
import { findSavedMapping } from '@/lib/column-mapping';
```

In `handleExport` (~line 184), add mapping to the request body:

```typescript
async function handleExport() {
  setExporting(true);
  try {
    // Get original column mapping if available
    const firstClaim = claims[0];
    const originalHeaders = firstClaim ? Object.keys(firstClaim.raw) : [];
    const savedMapping = originalHeaders.length > 0 ? findSavedMapping(originalHeaders) : null;

    const res = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        claims,
        format: exportFormat,
        type: 'corrected',
        columnMapping: savedMapping?.mapping ?? null,
      }),
    });
    // ... rest unchanged
```

**Step 2: Build reverse mapping in the export API**

In `app/api/export/route.ts`, extract columnMapping from the body (~line 13):

```typescript
const columnMapping: Record<string, string | null> | null = body.columnMapping ?? null;
```

Add a helper function to build the reverse label map (after the existing helpers, before `claimToRow`):

```typescript
/** Invert column mapping: ICDGuard field → original CSV header */
function buildHeaderLabels(
  mapping: Record<string, string | null> | null,
): Record<string, string> {
  if (!mapping) return {};
  const labels: Record<string, string> = {};
  for (const [csvHeader, field] of Object.entries(mapping)) {
    if (field && !labels[field]) {
      labels[field] = csvHeader;
    }
  }
  return labels;
}
```

**Step 3: Update `claimToRow` and `buildCsv` to use original labels**

Modify `claimToRow` to accept optional labels and use them as keys:

```typescript
const FIELD_TO_HEADER: Record<string, string> = {
  patientId: 'patient_id',
  patientName: 'patient_name',
  serviceDate: 'service_date',
  icdCode: 'icd_code',
  icdCode2: 'ecc',
  tariffCode: 'tariff_code',
  treatmentCode: 'treatment_code',
  quantity: 'quantity',
  amount: 'amount',
  provider: 'provider',
};

function claimToRow(
  claim: ValidatedClaim,
  labels: Record<string, string>,
): Record<string, string | number | undefined> {
  const h = (field: string) => labels[field] || FIELD_TO_HEADER[field] || field;
  return {
    [h('patientId')]: claim.patientId,
    [h('patientName')]: claim.patientName,
    [h('serviceDate')]: claim.serviceDate,
    [h('icdCode')]: claim.corrections['icdCode'] ?? claim.icdCode,
    [h('icdCode2')]: claim.corrections['icdCode2'] ?? claim.raw['ecc'] ?? claim.raw['icd_code2'] ?? claim.raw['icd2'],
    [h('tariffCode')]: claim.corrections['tariffCode'] ?? claim.tariffCode,
    [h('treatmentCode')]: claim.corrections['treatmentCode'] ?? claim.treatmentCode,
    [h('quantity')]: claim.quantity,
    [h('amount')]: claim.amount,
    [h('provider')]: claim.provider,
    status: claim.result.status,
  };
}
```

Update `buildCsv` to derive headers from the first row:

```typescript
function buildCsv(claims: ValidatedClaim[], labels: Record<string, string>): string {
  const rows = claims.map((c) => claimToRow(c, labels));
  if (rows.length === 0) return '';
  const headers = Object.keys(rows[0]);
  const dataRows = rows.map((row) =>
    headers.map((h) => JSON.stringify(row[h] ?? '')).join(','),
  );
  return [headers.join(','), ...dataRows].join('\n');
}
```

**Step 4: Wire up the mapping in the export handler**

Update the corrected data export section (~line 59-86) to build labels and pass them through:

```typescript
// Corrected data export
const labels = buildHeaderLabels(columnMapping);

if (format === 'csv') {
  const csv = buildCsv(claims, labels);
  // ... rest unchanged
}

if (format === 'xlsx') {
  const { utils, write } = await import('xlsx');
  const rows = claims.map((c) => claimToRow(c, labels));
  // ... rest unchanged
}
```

**Step 5: Commit**

```bash
git add ICDGuard/app/review/page.tsx ICDGuard/app/api/export/route.ts
git commit -m "feat: use original CSV column names in corrected data export"
```

---

### Task 6: Manual verification

**Step 1: Start the dev server**

```bash
cd ICDGuard && npm run dev
```

**Step 2: Test corrected export with mapped columns**

1. Upload a CSV with non-standard headers (e.g., "Member No", "ICD10", "Proc Code")
2. Map columns in the ColumnMapper
3. Review claims, make a correction
4. Export corrected data as CSV
5. Verify the exported CSV uses the original column names ("Member No", "ICD10", etc.) plus "status"

**Step 3: Test corrected export with auto-detected format**

1. Upload a CSV with standard headers (patient_id, icd_code, etc.)
2. Export corrected data
3. Verify it uses the standard generic headers (no regression)

**Step 4: Test report print fixes**

1. Upload any CSV, review claims
2. Generate an HTML report (Errors and Review)
3. Open the report, verify:
   - Summary section is compact (not a full page)
   - Table borders are darker
   - No extra line under patient name/ID/date
   - Filename appears in the header
4. Print preview (Ctrl+P), verify:
   - Status badges show in colour (green/red/orange)
   - Summary + first patient fit on page 1
   - Borders are clearly visible

**Step 5: Test line numbers**

1. Upload a file with 10+ lines
2. Generate a "Changes Only" report after correcting lines 3 and 7
3. Verify the # column shows 3 and 7, not 1 and 2

**Step 6: Commit any fixes if needed**
