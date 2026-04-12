# Report Format Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the card-based HTML report with a table-per-patient layout so changes and required actions are immediately visible to billing clerks.

**Architecture:** Add `icd_original` and `tariff_original` fields to `ReportRow` so the HTML renderer can show old→new inline. Rewrite `report-html.ts` to render a table per patient group instead of cards. Header and summary stats remain unchanged. No changes to CSV/XLSX/JSON exports or review page UI.

**Tech Stack:** TypeScript, Next.js, inline HTML/CSS (no external dependencies).

---

### Task 1: Add original code fields to ReportRow

**Files:**
- Modify: `ICDGuard/lib/export-report.ts:5-15` (ReportRow interface)
- Modify: `ICDGuard/lib/export-report.ts:77-110` (buildReportRows function)

**Step 1: Add fields to ReportRow interface**

Add two new optional fields after `tariff_code`:

```typescript
export interface ReportRow {
  patient_id: string;
  patient_name: string;
  service_date: string;
  icd_code: string;
  icd_original: string;
  tariff_code: string;
  tariff_original: string;
  status: string;
  issues_found: string;
  changes_made: string;
  suggestions: string;
}
```

`icd_code` keeps the current (corrected) value. `icd_original` holds the pre-correction value only when a change was made (empty string if no change). Same for tariff.

**Step 2: Populate original fields in buildReportRows**

In the `rows.push()` call (~line 91), change the icd/tariff fields:

```typescript
const icdCorrected = claim.corrections['icdCode'];
const icdOriginal = claim.icdCode ?? '';
const tariffCorrected = claim.corrections['tariffCode'];
const tariffOriginal = claim.tariffCode ?? '';

rows.push({
  patient_id: claim.patientId ?? '',
  patient_name: claim.patientName ?? '',
  service_date: claim.serviceDate ?? '',
  icd_code: icdCorrected ?? icdOriginal,
  icd_original: icdCorrected && icdCorrected !== icdOriginal ? icdOriginal : '',
  tariff_code: tariffCorrected ?? tariffOriginal,
  tariff_original: tariffCorrected && tariffCorrected !== tariffOriginal ? tariffOriginal : '',
  status: formatStatus(status),
  issues_found: buildIssues(claim),
  changes_made: buildChanges(claim),
  suggestions: buildSuggestions(claim),
});
```

**Step 3: Verify the app still compiles**

Run: `cd ICDGuard && npx next build 2>&1 | tail -5`
Expected: Build succeeds (CSV/XLSX/JSON exports reference ReportRow fields by key so new fields are harmlessly ignored).

**Step 4: Commit**

```bash
git add ICDGuard/lib/export-report.ts
git commit -m "feat: add icd_original and tariff_original to ReportRow"
```

---

### Task 2: Rewrite report-html.ts with table-per-patient layout

**Files:**
- Modify: `ICDGuard/lib/report-html.ts` (full rewrite of body, keep imports and helpers)

**Step 1: Replace the card rendering functions**

Remove `claimCard()` (lines 73-95) and `patientSection()` (lines 97-119). Replace with two new functions:

```typescript
function codeCell(current: string, original: string): string {
  if (!original) return `<td style="padding:6px 10px;border:1px solid #E2E8F0;font-size:0.8rem;white-space:nowrap;">${esc(current)}</td>`;
  return `<td style="padding:6px 10px;border:1px solid #E2E8F0;font-size:0.8rem;white-space:nowrap;"><span style="text-decoration:line-through;color:#94A3B8;">${esc(original)}</span> <span style="color:#059669;font-weight:600;">&rarr; ${esc(current)}</span></td>`;
}

function actionCell(row: ReportRow): string {
  const parts: string[] = [];
  if (row.changes_made) {
    for (const c of row.changes_made.split('; ')) {
      parts.push(`<div style="font-size:0.8rem;color:#1E293B;">${changeRow(c)}</div>`);
    }
  }
  if (row.suggestions) {
    for (const s of row.suggestions.split('; ')) {
      parts.push(`<div style="font-size:0.8rem;color:#1E293B;">${suggestionRow(s)}</div>`);
    }
  }
  return `<td style="padding:6px 10px;border:1px solid #E2E8F0;">${parts.join('') || '<span style="color:#CBD5E1;font-size:0.8rem;">&mdash;</span>'}</td>`;
}

function issuesCell(text: string): string {
  if (!text) return `<td style="padding:6px 10px;border:1px solid #E2E8F0;"><span style="color:#CBD5E1;font-size:0.8rem;">&mdash;</span></td>`;
  const items = text.split('; ').map(issueRow).join('');
  return `<td style="padding:6px 10px;border:1px solid #E2E8F0;">${items}</td>`;
}

function claimRow(r: ReportRow, idx: number): string {
  const bgColor = r.status === 'Rejected' ? '#FFF5F5' : r.status === 'Needs Review' ? '#FFFBEB' : '#F0FDF4';
  const borderColor = r.status === 'Rejected' ? '#FECACA' : r.status === 'Needs Review' ? '#FDE68A' : '#BBF7D0';
  return `<tr style="background:${bgColor};border-left:3px solid ${borderColor};">
    <td style="padding:6px 10px;border:1px solid #E2E8F0;text-align:center;font-size:0.75rem;color:#94A3B8;font-weight:600;">${idx + 1}</td>
    <td style="padding:6px 10px;border:1px solid #E2E8F0;font-size:0.8rem;white-space:nowrap;">${esc(r.service_date)}</td>
    ${codeCell(r.icd_code, r.icd_original)}
    ${codeCell(r.tariff_code, r.tariff_original)}
    <td style="padding:6px 10px;border:1px solid #E2E8F0;text-align:center;">${statusBadge(r.status)}</td>
    ${issuesCell(r.issues_found)}
    ${actionCell(r)}
  </tr>`;
}

function patientTable(group: PatientGroup): string {
  const rejected = group.rows.filter((r) => r.status === 'Rejected').length;
  const review = group.rows.filter((r) => r.status === 'Needs Review').length;
  const valid = group.rows.filter((r) => r.status === 'Valid').length;

  const miniStats: string[] = [];
  if (rejected) miniStats.push(`<span style="color:#DC2626;font-weight:600;">${rejected} error${rejected > 1 ? 's' : ''}</span>`);
  if (review) miniStats.push(`<span style="color:#D97706;font-weight:600;">${review} review</span>`);
  if (valid) miniStats.push(`<span style="color:#059669;font-weight:600;">${valid} valid</span>`);

  return `<div style="margin-bottom:28px;page-break-inside:avoid;">
    <div style="display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid #E2E8F0;padding-bottom:8px;margin-bottom:12px;">
      <div>
        <span style="font-size:1rem;font-weight:700;color:#1A3A6B;">${esc(group.patientName || group.patientId || 'Unknown Patient')}</span>
        ${group.patientName && group.patientId ? `<span style="font-size:0.8rem;color:#94A3B8;margin-left:10px;">ID: ${esc(group.patientId)}</span>` : ''}
      </div>
      <div style="font-size:0.8rem;display:flex;gap:12px;">${miniStats.join('')}
        <span style="color:#94A3B8;">${group.rows.length} line${group.rows.length !== 1 ? 's' : ''}</span>
      </div>
    </div>
    <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
      <thead>
        <tr style="background:#F1F5F9;">
          <th style="padding:8px 10px;border:1px solid #E2E8F0;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;color:#64748B;text-align:center;width:36px;">#</th>
          <th style="padding:8px 10px;border:1px solid #E2E8F0;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;color:#64748B;text-align:left;">Date</th>
          <th style="padding:8px 10px;border:1px solid #E2E8F0;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;color:#64748B;text-align:left;">ICD Code</th>
          <th style="padding:8px 10px;border:1px solid #E2E8F0;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;color:#64748B;text-align:left;">Tariff Code</th>
          <th style="padding:8px 10px;border:1px solid #E2E8F0;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;color:#64748B;text-align:center;">Status</th>
          <th style="padding:8px 10px;border:1px solid #E2E8F0;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;color:#64748B;text-align:left;">Issues</th>
          <th style="padding:8px 10px;border:1px solid #E2E8F0;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;color:#64748B;text-align:left;">Action Required</th>
        </tr>
      </thead>
      <tbody>
        ${group.rows.map((r, i) => claimRow(r, i)).join('')}
      </tbody>
    </table>
  </div>`;
}
```

**Step 2: Update buildReportHtml to use patientTable**

In the `buildReportHtml` function (~line 121), change the claims section from:

```typescript
${groups.map(patientSection).join('')}
```

to:

```typescript
${groups.map(patientTable).join('')}
```

**Step 3: Remove old claimCard and patientSection functions**

Delete the `claimCard()` function (lines 73-95) and `patientSection()` function (lines 97-119) — they are replaced by the new functions above.

**Step 4: Verify the app compiles**

Run: `cd ICDGuard && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 5: Manual test**

Upload a test CSV, generate an HTML report, and open it in a browser. Verify:
- Patient grouping with header and mini-stats
- Table rows with colour-coded backgrounds
- ICD/Tariff columns show strikethrough old → new when corrected
- Issues column shows errors/warnings with icons
- Action Required column shows changes and suggestions
- Summary stats at top still work

**Step 6: Commit**

```bash
git add ICDGuard/lib/report-html.ts
git commit -m "feat: replace card layout with table-per-patient in HTML report"
```

---

### Task 3: Update PatientGroup interface to use ReportRow

**Files:**
- Modify: `ICDGuard/lib/report-html.ts:40-44` (PatientGroup interface)

The `PatientGroup` interface currently types `rows` as `ReportRow[]` which already works. Verify that the `groupByPatient` function still works correctly with the new `icd_original` and `tariff_original` fields — no changes needed since it passes rows through untouched. This is a verification-only step.

**Step 1: Verify no type errors**

Run: `cd ICDGuard && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors.

---
