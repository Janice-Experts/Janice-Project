# Summary Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "Summary" report style to the export panel — a clean, no-frills checklist showing what needs changing per patient, alongside the existing "Detailed" report.

**Architecture:** New `reportStyle` state in review page, passed through the export API. A new `lib/report-summary-html.ts` builds the summary HTML. Existing `buildReportRows()` is reused for filtering — only the rendering differs. The `action_needed` field is computed from existing `changes_made` and `suggestions` fields.

**Tech Stack:** Next.js, React, TypeScript, inline HTML/CSS for report output

---

### Task 1: Add `reportStyle` state and UI to export panel

**Files:**
- Modify: `app/review/page.tsx:58-60` (state declarations)
- Modify: `app/review/page.tsx:293-340` (report panel UI)

**Step 1: Add state declaration**

At line 60, after the `reportFormat` state, add:

```typescript
const [reportStyle, setReportStyle] = useState<'summary' | 'detailed'>('summary');
```

**Step 2: Add Report Style radio group to panel**

In the report panel (line 294), insert a Report Style section before the existing Report Type section. The panel content should be ordered: Report Style → Report Type → Format → Generate button.

```tsx
<p className="text-xs font-semibold text-slate-700 mb-2">Report Style</p>
{([
  ['summary', 'Summary'],
  ['detailed', 'Detailed'],
] as const).map(([value, label]) => (
  <label key={value} className="flex items-center gap-2 text-sm text-slate-600 py-1 cursor-pointer">
    <input
      type="radio"
      name="reportStyle"
      value={value}
      checked={reportStyle === value}
      onChange={() => setReportStyle(value)}
      className="text-[#1a3a6b] focus:ring-[#1a3a6b]"
    />
    {label}
  </label>
))}
```

**Step 3: Pass `reportStyle` in the export request**

In `handleGenerateReport()` at line 215, add `reportStyle` to the JSON body:

```typescript
body: JSON.stringify({
  claims,
  format: reportFormat,
  type: 'report',
  reportType,
  reportStyle,
  acceptedIds: Array.from(acceptedIds),
  filename: summary.filename,
}),
```

**Step 4: Run dev server and visually verify the panel**

Run: `cd ICDGuard && npm run dev`
Expected: Export panel shows Report Style (Summary/Detailed) above Report Type. Default is Summary.

**Step 5: Commit**

```bash
git add app/review/page.tsx
git commit -m "feat: add report style toggle (summary/detailed) to export panel"
```

---

### Task 2: Create `buildSummaryReportHtml()`

**Files:**
- Create: `lib/report-summary-html.ts`

**Step 1: Create the summary HTML builder**

This file builds a clean, minimal HTML report. No colour-coded row backgrounds, no severity icons, no suggestion stars. Plain text status, arrow notation for changes, blank Action Needed when nothing to do.

```typescript
import { ReportRow, ReportType } from './export-report';

const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  errors: 'Errors Only',
  review: 'Needs Review Only',
  errors_review: 'Errors and Review',
  changes: 'Changes Only',
  full: 'Full Report',
};

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

interface PatientGroup {
  patientId: string;
  patientName: string;
  serviceDate: string;
  rows: ReportRow[];
}

function groupByPatientAndDate(rows: ReportRow[]): PatientGroup[] {
  const map = new Map<string, PatientGroup>();
  for (const r of rows) {
    const key = `${r.patient_id || '(no ID)'}|${r.service_date}`;
    if (!map.has(key)) {
      map.set(key, { patientId: r.patient_id, patientName: r.patient_name, serviceDate: r.service_date, rows: [] });
    }
    map.get(key)!.rows.push(r);
  }
  return Array.from(map.values());
}

function buildActionNeeded(row: ReportRow): string {
  const parts: string[] = [];
  // Changes already made (corrections applied)
  if (row.changes_made) {
    for (const c of row.changes_made.split('; ')) {
      parts.push(c);
    }
  }
  // Suggestions not yet applied
  if (row.suggestions) {
    for (const s of row.suggestions.split('; ')) {
      parts.push(s);
    }
  }
  return parts.join('; ');
}

function codeCell(current: string, original: string): string {
  if (!original) return `<td style="padding:6px 10px;border:1px solid #CBD5E1;font-size:0.85rem;">${esc(current)}</td>`;
  return `<td style="padding:6px 10px;border:1px solid #CBD5E1;font-size:0.85rem;">${esc(original)} &rarr; ${esc(current)}</td>`;
}

function summaryRow(r: ReportRow): string {
  const action = buildActionNeeded(r);
  return `<tr>
    <td style="padding:6px 10px;border:1px solid #CBD5E1;text-align:center;font-size:0.85rem;">${r.line_number}</td>
    ${codeCell(r.icd_code, r.icd_original)}
    ${codeCell(r.tariff_code, r.tariff_original)}
    <td style="padding:6px 10px;border:1px solid #CBD5E1;font-size:0.85rem;">${esc(r.status)}</td>
    <td style="padding:6px 10px;border:1px solid #CBD5E1;font-size:0.85rem;">${action ? esc(action) : ''}</td>
  </tr>`;
}

function patientTable(group: PatientGroup): string {
  return `<div style="margin-bottom:24px;page-break-inside:avoid;">
    <div style="padding-bottom:6px;margin-bottom:8px;border-bottom:1px solid #CBD5E1;">
      <span style="font-size:0.95rem;font-weight:700;color:#1E293B;">${esc(group.patientName || group.patientId || 'Unknown Patient')}</span>
      ${group.patientName && group.patientId ? `<span style="font-size:0.95rem;color:#1E293B;margin-left:10px;">ID: ${esc(group.patientId)}</span>` : ''}
      ${group.serviceDate ? `<span style="font-size:0.95rem;color:#1E293B;margin-left:10px;">&mdash; ${esc(group.serviceDate)}</span>` : ''}
    </div>
    <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
      <thead>
        <tr style="background:#F1F5F9;">
          <th style="padding:6px 10px;border:1px solid #CBD5E1;font-size:0.75rem;text-transform:uppercase;color:#64748B;text-align:center;width:5%;">#</th>
          <th style="padding:6px 10px;border:1px solid #CBD5E1;font-size:0.75rem;text-transform:uppercase;color:#64748B;text-align:left;width:15%;">ICD Code</th>
          <th style="padding:6px 10px;border:1px solid #CBD5E1;font-size:0.75rem;text-transform:uppercase;color:#64748B;text-align:left;width:15%;">Tariff Code</th>
          <th style="padding:6px 10px;border:1px solid #CBD5E1;font-size:0.75rem;text-transform:uppercase;color:#64748B;text-align:left;width:15%;">Status</th>
          <th style="padding:6px 10px;border:1px solid #CBD5E1;font-size:0.75rem;text-transform:uppercase;color:#64748B;text-align:left;width:50%;">Action Needed</th>
        </tr>
      </thead>
      <tbody>
        ${group.rows.map(summaryRow).join('')}
      </tbody>
    </table>
  </div>`;
}

export function buildSummaryReportHtml(rows: ReportRow[], rType: ReportType, filename?: string): string {
  const title = 'Claim ICD Validation Summary';
  const subtitle = REPORT_TYPE_LABELS[rType];
  const date = new Date().toLocaleDateString('en-ZA', { year: 'numeric', month: 'long', day: 'numeric' });
  const groups = groupByPatientAndDate(rows);

  const rejected = rows.filter((r) => r.status === 'Rejected').length;
  const review = rows.filter((r) => r.status === 'Needs Review').length;
  const valid = rows.filter((r) => r.status === 'Valid').length;
  const corrected = rows.filter((r) => r.changes_made).length;
  const statsLine = `${rows.length} lines | ${rejected} errors | ${review} needs review | ${valid} valid | ${corrected} corrected`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: white;
    color: #1E293B;
    line-height: 1.5;
    padding: 32px 40px;
    max-width: 1200px;
    margin: 0 auto;
  }
  @media print {
    body { padding: 0; }
    .no-print { display: none !important; }
    @page { size: A4 landscape; margin: 1.5cm; }
  }
</style>
</head>
<body>

<div style="margin-bottom:24px;">
  <div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#64748B;margin-bottom:4px;">ICDGuard</div>
  <h1 style="font-size:1.3rem;font-weight:700;color:#1E293B;margin-bottom:4px;">${title}${filename ? ` &mdash; ${esc(filename)}` : ''}</h1>
  <p style="font-size:0.85rem;color:#64748B;">${subtitle} &mdash; ${date}</p>
  <p style="font-size:0.85rem;color:#475569;margin-top:8px;">${statsLine}</p>
  <button class="no-print" onclick="window.print()" style="margin-top:8px;background:#1A3A6B;color:white;border:none;padding:6px 16px;border-radius:6px;font-size:0.8rem;font-weight:600;cursor:pointer;">Print (use Landscape)</button>
</div>

${groups.map(patientTable).join('')}

<div style="border-top:1px solid #E2E8F0;padding-top:12px;margin-top:16px;font-size:0.75rem;color:#94A3B8;display:flex;justify-content:space-between;">
  <span>Generated by ICDGuard &mdash; ${date}</span>
  <span>Verify all changes in your billing system before submission.</span>
</div>

</body>
</html>`;
}
```

**Step 2: Commit**

```bash
git add lib/report-summary-html.ts
git commit -m "feat: add summary report HTML builder"
```

---

### Task 3: Route export API to summary or detailed builder

**Files:**
- Modify: `app/api/export/route.ts:6-14` (parse `reportStyle`)
- Modify: `app/api/export/route.ts:48-56` (route HTML builder)

**Step 1: Import the new builder**

At line 4, add:

```typescript
import { buildSummaryReportHtml } from '@/lib/report-summary-html';
```

**Step 2: Parse `reportStyle` from request body**

At line 14, after `const reportType`, add:

```typescript
const reportStyle: 'summary' | 'detailed' = body.reportStyle ?? 'detailed';
```

**Step 3: Route HTML format to correct builder**

Replace the HTML block (lines 48-56) with:

```typescript
if (format === 'html') {
  const html = reportStyle === 'summary'
    ? buildSummaryReportHtml(reportRows, reportType, filename)
    : buildReportHtml(reportRows, reportType, filename);
  return new NextResponse(html, {
    headers: {
      'Content-Type': 'text/html',
      'Content-Disposition': `attachment; filename="validation_report.html"`,
    },
  });
}
```

**Step 4: Route JSON format to include `action_needed` for summary**

Replace the JSON block (lines 44-46) with:

```typescript
if (format === 'json') {
  if (reportStyle === 'summary') {
    const summaryRows = reportRows.map((r) => ({
      line_number: r.line_number,
      patient_id: r.patient_id,
      patient_name: r.patient_name,
      service_date: r.service_date,
      icd_code: r.icd_code,
      icd_original: r.icd_original,
      tariff_code: r.tariff_code,
      tariff_original: r.tariff_original,
      status: r.status,
      action_needed: [r.changes_made, r.suggestions].filter(Boolean).join('; '),
    }));
    return NextResponse.json({ reportType, reportStyle, totalRows: summaryRows.length, rows: summaryRows });
  }
  return NextResponse.json({ reportType, totalRows: reportRows.length, rows: reportRows });
}
```

**Step 5: Run dev server and test end-to-end**

Run: `cd ICDGuard && npm run dev`
1. Import a test CSV file
2. Open export panel → select Summary style, Errors and Review type, HTML format → Generate
3. Verify the downloaded HTML is the clean summary layout
4. Repeat with JSON format — verify `action_needed` field present, no `issues_found`/`changes_made`/`suggestions`
5. Switch to Detailed style → verify original detailed report still works

**Step 6: Commit**

```bash
git add app/api/export/route.ts
git commit -m "feat: route export API to summary or detailed report builder"
```

---

### Task 4: Update filename for summary reports

**Files:**
- Modify: `app/review/page.tsx:225-229` (filename logic)

**Step 1: Include style in exported filename**

Change the filename construction in `handleGenerateReport` to distinguish summary from detailed:

```typescript
const styleTag = reportStyle === 'summary' ? '-summary' : '-report';
const exportedFilename = await downloadBlob(blob, `${base}${styleTag}.${ext}`, descMap[reportFormat], ext);
```

**Step 2: Test both styles produce correctly named files**

Expected: Summary → `filename-summary.html`, Detailed → `filename-report.html`

**Step 3: Commit**

```bash
git add app/review/page.tsx
git commit -m "feat: distinguish summary vs detailed in exported report filename"
```
