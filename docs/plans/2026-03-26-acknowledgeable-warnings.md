# Acknowledgeable Warnings Implementation Plan

> **Status:** COMPLETED — implemented and smoke tested 2026-03-26. Commit `fcc36f3`.

**Goal:** Allow users to acknowledge informational warnings (PMB, ICD_UNSPECIFIED) so claims flip to valid/green, and stop showing these in the batch correction bar.

**Architecture:** Client-side only. A Set of accepted claim IDs lives in review page state. When accepted, effective status overrides to 'valid' if no non-acknowledgeable issues remain. Batch bar skips acknowledgeable issue codes.

**Tech Stack:** React state (useState), TypeScript, Tailwind CSS

**Additional changes made during implementation:**
- DEMO_AGE_NEONATAL changed from warning to error (P-codes >28 days are rejected by schemes)
- Expanded claims pinned to current filter to prevent card collapse during editing (bug fix)
- Test data expanded with treatment cross-check scenarios

---

### Task 1: Filter acknowledgeable issues from BatchCorrectionBar

**Files:**
- Modify: `app/review/page.tsx:21-44` (computeBatchIssues function)

**Step 1: Add skip for PMB_CONDITION and ICD_UNSPECIFIED**

In `computeBatchIssues()`, line 25, extend the existing skip:

```typescript
// Before (line 25):
if (issue.code === 'DUPLICATE_CLAIM') continue;

// After:
if (issue.code === 'DUPLICATE_CLAIM') continue;
if (issue.code === 'PMB_CONDITION' || issue.code === 'ICD_UNSPECIFIED') continue;
```

**Step 2: Verify dev server shows no batch rows for PMB/unspecified**

Run: Upload `features-1-3-test.csv`, check the batch correction bar.
Expected: No batch row for J06.9 unspecified or PMB. Treatment mismatch and other errors still appear if 2+ claims share them.

**Step 3: Commit**

```bash
git add app/review/page.tsx
git commit -m "feat: exclude PMB and ICD_UNSPECIFIED from batch correction bar"
```

---

### Task 2: Define acknowledgeable issue codes constant

**Files:**
- Modify: `app/review/page.tsx` (top of file, after imports)

**Step 1: Add constant**

After the imports (line 12), add:

```typescript
/** Warning codes the user can acknowledge without correcting the code */
const ACKNOWLEDGEABLE_CODES = new Set(['PMB_CONDITION', 'ICD_UNSPECIFIED']);
```

**Step 2: Refactor the batch skip to use it**

Replace the line added in Task 1:

```typescript
// Before:
if (issue.code === 'PMB_CONDITION' || issue.code === 'ICD_UNSPECIFIED') continue;

// After:
if (ACKNOWLEDGEABLE_CODES.has(issue.code)) continue;
```

**Step 3: Commit**

```bash
git add app/review/page.tsx
git commit -m "refactor: extract ACKNOWLEDGEABLE_CODES constant for reuse"
```

---

### Task 3: Add accepted state and pass it down

**Files:**
- Modify: `app/review/page.tsx` (state + props)
- Modify: `components/ClaimGroupCard.tsx` (accept props on component)

**Step 1: Add state and handler in review page**

In `ReviewPage()`, after the `exporting` state (line 51), add:

```typescript
const [acceptedIds, setAcceptedIds] = useState<Set<string>>(new Set());

function handleAccept(id: string, accepted: boolean) {
  setAcceptedIds((prev) => {
    const next = new Set(prev);
    if (accepted) next.add(id);
    else next.delete(id);
    return next;
  });
}
```

**Step 2: Create effective status helper**

Below `handleAccept`, add:

```typescript
function effectiveStatus(claim: ValidatedClaim): ClaimStatus {
  if (!acceptedIds.has(claim.id)) return claim.result.status;
  // Only override if all remaining issues are acknowledgeable
  const hasNonAcknowledgeable = claim.result.issues.some(
    (i) => !ACKNOWLEDGEABLE_CODES.has(i.code)
  );
  if (hasNonAcknowledgeable) return claim.result.status;
  return 'valid';
}
```

**Step 3: Update KPI bar counts to use effective status**

Replace the KpiBar JSX (lines 206-211):

```tsx
<KpiBar
  total={claims.length}
  valid={claims.filter((c) => effectiveStatus(c) === 'valid').length}
  needsReview={claims.filter((c) => effectiveStatus(c) === 'needs_review').length}
  rejected={claims.filter((c) => effectiveStatus(c) === 'rejected').length}
/>
```

**Step 4: Update filter logic to use effective status**

Replace line 163:

```typescript
// Before:
const filtered = filter === 'all' ? claims : claims.filter((c) => c.result.status === filter);

// After:
const filtered = filter === 'all' ? claims : claims.filter((c) => effectiveStatus(c) === filter);
```

**Step 5: Update filter tab counts**

In the filter tabs JSX (line 236), replace:

```typescript
// Before:
({s === 'all' ? claims.length : claims.filter((c) => c.result.status === s).length})

// After:
({s === 'all' ? claims.length : claims.filter((c) => effectiveStatus(c) === s).length})
```

**Step 6: Pass acceptedIds, onAccept, and effectiveStatus to ClaimGroupCard**

Update the ClaimGroupCard JSX (line 243-244):

```tsx
<ClaimGroupCard
  key={group.groupKey}
  group={group}
  onChange={handleChange}
  acceptedIds={acceptedIds}
  onAccept={handleAccept}
  effectiveStatus={effectiveStatus}
/>
```

**Step 7: Update ClaimGroupCard props interface**

In `components/ClaimGroupCard.tsx`, update the interface (lines 7-11):

```typescript
interface ClaimGroupCardProps {
  group: ClaimGroup;
  onChange: (id: string, corrections: Record<string, string>) => void;
  onExpandChange?: (id: string, expanded: boolean) => void;
  acceptedIds: Set<string>;
  onAccept: (id: string, accepted: boolean) => void;
  effectiveStatus: (claim: ValidatedClaim) => ClaimStatus;
}
```

**Step 8: Commit**

```bash
git add app/review/page.tsx components/ClaimGroupCard.tsx
git commit -m "feat: add accepted warnings state and effective status helper"
```

---

### Task 4: Update ClaimGroupCard to use effective status and show checkbox

**Files:**
- Modify: `components/ClaimGroupCard.tsx`

**Step 1: Add ACKNOWLEDGEABLE_CODES constant at top of file**

After imports (line 5):

```typescript
const ACKNOWLEDGEABLE_CODES = new Set(['PMB_CONDITION', 'ICD_UNSPECIFIED']);
```

**Step 2: Update group header badge to use effective status**

In the `ClaimGroupCard` component, compute the effective group status for the badge. Replace the group header status badge (line 46-48):

```tsx
{/* Compute effective group status from items */}
{(() => {
  const effectiveGroupStatus = group.items.reduce<ClaimStatus>((worst, item) => {
    const s = effectiveStatus(item);
    const rank = { rejected: 2, needs_review: 1, valid: 0 } as const;
    return rank[s] > rank[worst] ? s : worst;
  }, 'valid');
  return (
    <span className={`text-xs font-semibold px-3 py-1 rounded-full ${STATUS_BADGE[effectiveGroupStatus]}`}>
      {STATUS_LABEL[effectiveGroupStatus]}
    </span>
  );
})()}
```

**Step 3: Pass new props down to LineItem**

Update the LineItem call inside the `.map()` (lines 52-61):

```tsx
{group.items.map((claim, idx) => (
  <LineItem
    key={claim.id}
    claim={claim}
    lineNumber={idx + 1}
    expanded={expandedId === claim.id}
    onToggle={() => handleToggle(claim.id)}
    onChange={onChange}
    isLast={idx === group.items.length - 1}
    accepted={acceptedIds.has(claim.id)}
    onAccept={onAccept}
    effectiveStatus={effectiveStatus}
  />
))}
```

**Step 4: Update LineItemProps and destructuring**

```typescript
interface LineItemProps {
  claim: ValidatedClaim;
  lineNumber: number;
  expanded: boolean;
  onToggle: () => void;
  onChange: (id: string, corrections: Record<string, string>) => void;
  isLast: boolean;
  accepted: boolean;
  onAccept: (id: string, accepted: boolean) => void;
  effectiveStatus: (claim: ValidatedClaim) => ClaimStatus;
}

function LineItem({ claim, lineNumber, expanded, onToggle, onChange, isLast, accepted, onAccept, effectiveStatus }: LineItemProps) {
```

**Step 5: Compute whether this claim can be acknowledged**

Inside `LineItem`, after the `issuesByField` map (after line 140), add:

```typescript
const canAcknowledge =
  claim.result.issues.length > 0 &&
  claim.result.issues.every((i) => ACKNOWLEDGEABLE_CODES.has(i.code));

const claimEffectiveStatus = effectiveStatus(claim);
```

**Step 6: Update collapsed row dots to reflect effective status**

Replace the ICD dot colour (line 204):

```tsx
// Before:
<span className={`w-2 h-2 rounded-full shrink-0 ${icdIssue ? (icdIssue.severity === 'error' ? 'bg-red-400' : 'bg-amber-400') : 'bg-green-400'}`} />

// After:
<span className={`w-2 h-2 rounded-full shrink-0 ${
  accepted && canAcknowledge ? 'bg-green-400'
    : icdIssue ? (icdIssue.severity === 'error' ? 'bg-red-400' : 'bg-amber-400')
    : 'bg-green-400'
}`} />
```

Same for the tariff dot (line 217):

```tsx
<span className={`w-2 h-2 rounded-full shrink-0 ${
  accepted && canAcknowledge ? 'bg-green-400'
    : tariffIssue ? (tariffIssue.severity === 'error' ? 'bg-red-400' : 'bg-amber-400')
    : 'bg-green-400'
}`} />
```

**Step 7: Add the Accept Warnings checkbox in the expanded view**

After the "Other issues" section (after line 306, before the closing `</div>` of the expanded block), add:

```tsx
{canAcknowledge && (
  <div className="border-t border-slate-100 px-5 py-3 bg-green-50/50 flex items-center gap-3">
    <input
      type="checkbox"
      id={`accept-${claim.id}`}
      checked={accepted}
      onChange={(e) => {
        e.stopPropagation();
        onAccept(claim.id, e.target.checked);
      }}
      className="w-4 h-4 rounded border-slate-300 text-green-600 focus:ring-green-500 accent-green-600"
    />
    <label
      htmlFor={`accept-${claim.id}`}
      className="text-xs font-medium text-slate-600 cursor-pointer select-none"
    >
      Accept warnings — I have reviewed and these are correct
    </label>
  </div>
)}
```

**Step 8: Commit**

```bash
git add components/ClaimGroupCard.tsx
git commit -m "feat: add accept warnings checkbox to claim cards"
```

---

### Task 5: Update export status counts to respect accepted warnings

**Files:**
- Modify: `app/review/page.tsx` (handleExport function)

**Step 1: Update export stats to use effectiveStatus**

In `handleExport`, replace the status counting block (lines 129-131):

```typescript
// Before:
const valid = claims.filter((c) => c.result.status === 'valid').length;
const needsReview = claims.filter((c) => c.result.status === 'needs_review').length;
const rejected = claims.filter((c) => c.result.status === 'rejected').length;

// After:
const valid = claims.filter((c) => effectiveStatus(c) === 'valid').length;
const needsReview = claims.filter((c) => effectiveStatus(c) === 'needs_review').length;
const rejected = claims.filter((c) => effectiveStatus(c) === 'rejected').length;
```

**Step 2: Commit**

```bash
git add app/review/page.tsx
git commit -m "feat: export stats respect accepted warnings"
```

---

### Task 6: Manual smoke test

**No files modified — verification only.**

**Step 1: Upload features-1-3-test.csv (GoodX)**

Expected batch correction bar: NO rows for J06.9 unspecified or PMB. Treatment mismatch rows may appear if 2+ claims share the same mismatch.

**Step 2: Test accept checkbox on SPEC01 (J06.9 unspecified)**

- Expand SPEC01 (Linda Adams)
- Checkbox should appear: "Accept warnings — I have reviewed and these are correct"
- Tick it — dots should go green, group badge should update
- KPI bar "Valid" count should increase by 1, "Review" decrease by 1
- Filter to "Valid" — SPEC01 should appear

**Step 3: Test accept checkbox on a PMB claim (VALID02 if K35.8 triggers PMB)**

Same flow — checkbox visible, ticking flips to green.

**Step 4: Test that TREATMENT_MISMATCH claims do NOT get checkbox**

- Expand TX02 (Zanele Ngcobo, K35.8 + cardiac tariff 0073)
- No "Accept warnings" checkbox should appear — must fix the code

**Step 5: Test mixed issues**

- If a claim has both ICD_UNSPECIFIED and TREATMENT_MISMATCH, no checkbox until mismatch is fixed

**Step 6: Test toggle**

- Accept a claim, then uncheck — should revert to amber/review
