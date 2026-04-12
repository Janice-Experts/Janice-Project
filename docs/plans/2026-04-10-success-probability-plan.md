# Success Probability Score Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a per-line and per-claim probability score predicting scheme payment likelihood, displayed in the UI and reports.

**Architecture:** A pure function `calcLineScore()` in `lib/probability.ts` takes a claim's issues and returns 0-100. Each issue code has a multiplier; they compound. Claim score = min of line scores. The score is computed at render time from existing validation data — no new validation pass needed.

**Tech Stack:** TypeScript, React, Next.js

---

### Task 1: Create scoring engine (`lib/probability.ts`)

**Files:**
- Create: `lib/probability.ts`

**Step 1: Create the scoring module**

```typescript
import type { ValidationIssue } from './types';

const ACKNOWLEDGEABLE_CODES = new Set(['PMB_CONDITION', 'ICD_UNSPECIFIED']);

/** Multiplier per issue code. Missing codes default to 1.0 (no impact). */
const ISSUE_MULTIPLIERS: Record<string, number> = {
  // Fatal — guaranteed rejection
  MISSING_ICDCODE: 0,
  MISSING_TARIFFCODE: 0,
  MISSING_PATIENTID: 0,
  MISSING_SERVICEDATE: 0,
  ICD_INVALID: 0,
  TARIFF_INVALID: 0,
  ICD_ECC_AS_PRIMARY: 0,
  DATE_FUTURE_SERVICE: 0,
  DATE_BEFORE_BIRTH: 0,
  // High risk
  DEMO_GENDER_MISMATCH: 0.20,
  DEMO_AGE_NEONATAL: 0.25,
  DEMO_AGE_INFANT: 0.25,
  // Medium risk
  ICD_UNSPECIFIED: 0.60,
  TREATMENT_MISMATCH: 0.60,
  DUPLICATE_CLAIM: 0.50,
  DATE_STALE_CLAIM: 0.60,
  // Low risk
  ICD_MISSING_ECC: 0.85,
  DEMO_AGE_PAEDIATRIC: 0.85,
  DEMO_AGE_CHILD: 0.85,
  DEMO_AGE_ADULT_ONLY: 0.85,
  // Boost
  PMB_CONDITION: 1.05,
};

/**
 * Calculate success probability for a single claim line.
 * Returns a number 0–100 (percentage).
 *
 * @param issues - The validation issues on this line
 * @param accepted - Whether the user has accepted/acknowledged this line's warnings
 */
export function calcLineScore(issues: ValidationIssue[], accepted: boolean): number {
  let score = 1.0;

  for (const issue of issues) {
    // Accepted lines: skip acknowledgeable warnings
    if (accepted && ACKNOWLEDGEABLE_CODES.has(issue.code)) continue;

    const multiplier = ISSUE_MULTIPLIERS[issue.code] ?? 1.0;
    score *= multiplier;
    if (score === 0) return 0; // short-circuit
  }

  return Math.min(Math.round(score * 100), 100);
}

/**
 * Calculate claim score from individual line scores.
 * Returns the minimum (weakest line drags claim down).
 */
export function calcClaimScore(lineScores: number[]): number {
  if (lineScores.length === 0) return 100;
  return Math.min(...lineScores);
}

/**
 * Return a colour class string based on the score.
 * 90-100 green, 60-89 amber, 0-59 red.
 */
export function scoreColor(score: number): { text: string; bg: string } {
  if (score >= 90) return { text: 'text-green-600', bg: 'bg-green-100' };
  if (score >= 60) return { text: 'text-amber-600', bg: 'bg-amber-100' };
  return { text: 'text-red-600', bg: 'bg-red-100' };
}

/**
 * Return an inline CSS colour for HTML reports based on score.
 */
export function scoreHtmlColor(score: number): string {
  if (score >= 90) return '#059669';
  if (score >= 60) return '#D97706';
  return '#DC2626';
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd ICDGuard && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add lib/probability.ts
git commit -m "feat: add success probability scoring engine"
```

---

### Task 2: Show line score on ClaimGroupCard collapsed row

**Files:**
- Modify: `components/ClaimGroupCard.tsx:1-8` (imports)
- Modify: `components/ClaimGroupCard.tsx:214-267` (LineItem collapsed row)

**Step 1: Add import**

At the top of `ClaimGroupCard.tsx`, add:

```typescript
import { calcLineScore, scoreColor } from '@/lib/probability';
```

**Step 2: Compute score in LineItem**

Inside the `LineItem` function, after the `canAcknowledge` variable (around line 171), add:

```typescript
const lineScore = calcLineScore(claim.result.issues, accepted);
const lineScoreStyle = scoreColor(lineScore);
```

**Step 3: Display score in collapsed row**

In the collapsed row div (the `div[role="button"]` around line 218-267), add the score badge between the tariff code section and the chevron. Insert before the `{/* Chevron */}` comment (around line 257):

```tsx
{/* Score */}
<span className={`text-xs font-bold px-2 py-0.5 rounded-full ${lineScoreStyle.text} ${lineScoreStyle.bg}`}>
  {lineScore}%
</span>
```

**Step 4: Verify TypeScript compiles**

Run: `cd ICDGuard && npx tsc --noEmit`

**Step 5: Commit**

```bash
git add components/ClaimGroupCard.tsx
git commit -m "feat: show line probability score on collapsed claim rows"
```

---

### Task 3: Show claim score on ClaimGroupCard header

**Files:**
- Modify: `components/ClaimGroupCard.tsx:1-8` (imports — already added in Task 2)
- Modify: `components/ClaimGroupCard.tsx:42-65` (group header)

**Step 1: Compute claim score in group header**

Inside the ClaimGroupCard component, within the IIFE that computes `effectiveGroupStatus` (lines 53-64), also compute the claim score. Replace the IIFE block with:

```tsx
{(() => {
  const effectiveGroupStatus = group.items.reduce<ClaimStatus>((worst, item) => {
    const s = effectiveStatus(item);
    const rank: Record<ClaimStatus, number> = { rejected: 2, needs_review: 1, valid: 0 };
    return rank[s] > rank[worst] ? s : worst;
  }, 'valid');
  const claimScore = Math.min(...group.items.map((item) => {
    const isAccepted = acceptedIds.has(item.id) && item.result.issues.every((i) => ACKNOWLEDGEABLE_CODES.has(i.code));
    return calcLineScore(item.result.issues, isAccepted);
  }));
  const claimScoreColor = scoreColor(claimScore);
  return (
    <div className="flex items-center gap-3">
      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${claimScoreColor.text} ${claimScoreColor.bg}`}>
        {claimScore}%
      </span>
      <span className={`text-xs font-semibold px-3 py-1 rounded-full ${STATUS_BADGE[effectiveGroupStatus]}`}>
        {STATUS_LABEL[effectiveGroupStatus]}
      </span>
    </div>
  );
})()}
```

Note: `ACKNOWLEDGEABLE_CODES` is already defined at line 9 of this file. `calcLineScore` and `scoreColor` were imported in Task 2.

**Step 2: Verify TypeScript compiles**

Run: `cd ICDGuard && npx tsc --noEmit`

**Step 3: Commit**

```bash
git add components/ClaimGroupCard.tsx
git commit -m "feat: show claim probability score in group header"
```

---

### Task 4: Add batch average score to KpiBar

**Files:**
- Modify: `components/KpiBar.tsx:1-6` (props)
- Modify: `components/KpiBar.tsx:8-18` (render)
- Modify: `app/review/page.tsx:6` (imports)
- Modify: `app/review/page.tsx:374-379` (KpiBar usage)

**Step 1: Add `avgScore` prop to KpiBar**

Update the interface and component:

```typescript
interface KpiBarProps {
  total: number;
  valid: number;
  needsReview: number;
  rejected: number;
  avgScore: number;
}

export default function KpiBar({ total, valid, needsReview, rejected, avgScore }: KpiBarProps) {
  const passRate = total > 0 ? Math.round((valid / total) * 100) : 0;
  const scoreAccent = avgScore >= 90 ? 'border-green-500' : avgScore >= 60 ? 'border-amber-500' : 'border-red-500';
  const scoreValueClass = avgScore >= 90 ? 'text-green-600' : avgScore >= 60 ? 'text-amber-600' : 'text-red-600';

  return (
    <div role="region" aria-label="Claim summary" className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-6">
      <KpiCard label="Total Claims" value={total} accent="border-[#1a3a6b]" valueClass="text-[#1a3a6b]" />
      <KpiCard label="Valid" value={valid} sub={`${passRate}% pass rate`} accent="border-green-500" valueClass="text-green-600" />
      <KpiCard label="Needs Review" value={needsReview} accent="border-amber-500" valueClass="text-amber-600" />
      <KpiCard label="Rejected" value={rejected} accent="border-red-500" valueClass="text-red-600" />
      <KpiCard label="Avg. Success" value={avgScore} sub="probability %" accent={scoreAccent} valueClass={scoreValueClass} />
    </div>
  );
}
```

**Step 2: Compute and pass avgScore in review page**

In `app/review/page.tsx`, add the import at the top:

```typescript
import { calcLineScore } from '@/lib/probability';
```

Then update the KpiBar usage (around line 374). Replace the existing `<KpiBar ... />` with:

```tsx
<KpiBar
  total={claims.length}
  valid={claims.filter((c) => effectiveStatus(c) === 'valid').length}
  needsReview={claims.filter((c) => effectiveStatus(c) === 'needs_review').length}
  rejected={claims.filter((c) => effectiveStatus(c) === 'rejected').length}
  avgScore={claims.length > 0 ? Math.round(claims.reduce((sum, c) => {
    const isAccepted = acceptedIds.has(c.id) && c.result.issues.every((i) => !['PMB_CONDITION', 'ICD_UNSPECIFIED'].includes(i.code) ? false : true);
    return sum + calcLineScore(c.result.issues, isAccepted);
  }, 0) / claims.length) : 100}
/>
```

Actually, for cleanliness, compute the average before the JSX. Near where the filter/status/claims logic is (around line 120-130 of the page), or just before the return, compute:

```typescript
const avgScore = claims.length > 0
  ? Math.round(claims.reduce((sum, c) => {
      const isAccepted = acceptedIds.has(c.id) && c.result.issues.every((i) => ACKNOWLEDGEABLE_CODES.has(i.code));
      return sum + calcLineScore(c.result.issues, isAccepted);
    }, 0) / claims.length)
  : 100;
```

Note: `ACKNOWLEDGEABLE_CODES` is already imported in this file (line ~2-3 area, check the imports). If not, import it from `lib/types` or define it locally as `new Set(['PMB_CONDITION', 'ICD_UNSPECIFIED'])`.

Then pass `avgScore={avgScore}` to KpiBar.

**Step 3: Verify TypeScript compiles**

Run: `cd ICDGuard && npx tsc --noEmit`

**Step 4: Commit**

```bash
git add components/KpiBar.tsx app/review/page.tsx
git commit -m "feat: show batch average probability score in KPI bar"
```

---

### Task 5: Add probability to ReportRow and report builders

**Files:**
- Modify: `lib/export-report.ts:5-18` (ReportRow interface)
- Modify: `lib/export-report.ts:81-122` (buildReportRows)
- Modify: `lib/report-html.ts:105-164` (detailed report tables)
- Modify: `lib/report-summary-html.ts` (summary report tables)

**Step 1: Add probability field to ReportRow**

In `lib/export-report.ts`, add to the `ReportRow` interface:

```typescript
export interface ReportRow {
  line_number: number;
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
  probability: number;   // <-- add this
}
```

**Step 2: Import and compute probability in buildReportRows**

At the top of `lib/export-report.ts`, add:

```typescript
import { calcLineScore } from './probability';
```

In the `buildReportRows` function, where each row is pushed (around line 100-113), add the probability field. The `accepted` status is already computed via `effectiveStatus`. A line is accepted if `acceptedIds.has(claim.id)` and all issues are acknowledgeable. Compute:

```typescript
const isAccepted = acceptedIds.has(claim.id) && claim.result.issues.every((i) => ACKNOWLEDGEABLE_CODES.has(i.code));
```

Then in the row object add:

```typescript
probability: calcLineScore(claim.result.issues, isAccepted),
```

**Step 3: Add probability column to detailed report HTML**

In `lib/report-html.ts`:

1. Import `scoreHtmlColor` from `./probability`:
   ```typescript
   import { scoreHtmlColor } from './probability';
   ```

2. In the `claimRow` function (line 105), add a probability cell after the status cell (line 113):
   ```typescript
   <td style="padding:6px 10px;border:1.5px solid #64748B;text-align:center;font-size:0.85rem;font-weight:700;color:${scoreHtmlColor(r.probability)};">${r.probability}%</td>
   ```

3. In the `patientTable` function header — add a column header after "Status" (line 154):
   ```html
   <th style="padding:8px 10px;border:1.5px solid #64748B;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;color:#64748B;text-align:center;">Score</th>
   ```

4. Update the `<colgroup>` widths (lines 141-148) to make room for the new column. Adjust to:
   ```html
   <col style="width:3%;">    <!-- # -->
   <col style="width:10%;">   <!-- ICD -->
   <col style="width:10%;">   <!-- Tariff -->
   <col style="width:8%;">    <!-- Status -->
   <col style="width:6%;">    <!-- Score -->
   <col style="width:31%;">   <!-- Issues -->
   <col style="width:32%;">   <!-- Action -->
   ```

5. Add claim score to the patient header `miniStats`. After the valid count, add:
   ```typescript
   const claimScore = Math.min(...group.rows.map((r) => r.probability));
   miniStats.push(`<span style="color:${scoreHtmlColor(claimScore)};font-weight:600;">${claimScore}% score</span>`);
   ```

**Step 4: Add probability column to summary report HTML**

In `lib/report-summary-html.ts`:

1. Import `scoreHtmlColor` from `./probability`:
   ```typescript
   import { scoreHtmlColor } from './probability';
   ```

2. Add a "Score" column to the table. Update column widths to: # 5%, ICD 14%, Tariff 14%, Status 12%, Score 7%, Action Needed 48%.

3. Add a header `<th>` for "Score" after "Status".

4. In the row function, add after the status cell:
   ```typescript
   <td style="padding:6px 10px;border:1px solid #CBD5E1;text-align:center;font-size:0.85rem;font-weight:700;color:${scoreHtmlColor(r.probability)};">${r.probability}%</td>
   ```

5. Update the stats line to include the average score:
   ```typescript
   const avgScore = rows.length > 0 ? Math.round(rows.reduce((s, r) => s + r.probability, 0) / rows.length) : 100;
   const statsLine = `${rows.length} lines | ... | avg. ${avgScore}% score`;
   ```

**Step 5: Verify TypeScript compiles**

Run: `cd ICDGuard && npx tsc --noEmit`

**Step 6: Commit**

```bash
git add lib/export-report.ts lib/probability.ts lib/report-html.ts lib/report-summary-html.ts
git commit -m "feat: add probability score to report rows and HTML reports"
```

---

### Task 6: Add probability to export API JSON and CSV/XLSX reports

**Files:**
- Modify: `app/api/export/route.ts:99-109` (REPORT_HEADERS)
- Modify: `app/api/export/route.ts:47-62` (JSON summary rows)

**Step 1: Add probability to REPORT_HEADERS and REPORT_LABELS**

In the export route, update the report header constants:

```typescript
const REPORT_HEADERS = [
  'patient_id', 'patient_name', 'service_date',
  'icd_code', 'tariff_code', 'status', 'probability',
  'issues_found', 'changes_made', 'suggestions',
] as const;

const REPORT_LABELS: Record<string, string> = {
  patient_id: 'Patient ID', patient_name: 'Patient Name', service_date: 'Service Date',
  icd_code: 'ICD Code', tariff_code: 'Tariff Code', status: 'Status', probability: 'Score %',
  issues_found: 'Issues Found', changes_made: 'Changes Made', suggestions: 'Suggestions',
};
```

**Step 2: Add probability to JSON summary rows**

In the summary JSON mapping (inside the `if (reportStyle === 'summary')` block), add `probability: r.probability` to the mapped object.

**Step 3: Verify TypeScript compiles**

Run: `cd ICDGuard && npx tsc --noEmit`

**Step 4: Commit**

```bash
git add app/api/export/route.ts
git commit -m "feat: include probability score in CSV/XLSX/JSON report exports"
```
