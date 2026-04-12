# Dashboard Date Grouping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the 10-session limit on the dashboard and group sessions by day/week/month with a segmented control toggle.

**Architecture:** Add `createdAt` (ISO string) to `SessionSummary`. Remove all slice limits. Convert `DashboardTable` into a grouped, collapsible table with a Day|Week|Month segmented control. Existing sessions without `createdAt` are backfilled with a fallback group.

**Tech Stack:** Next.js 16 (App Router), TypeScript, React (client component), Tailwind CSS v4

---

### Task 1: Add `createdAt` to SessionSummary type

**Files:**
- Modify: `lib/types.ts:43-63`

**Step 1: Add the field**

In `SessionSummary`, add `createdAt` as an optional string (optional so existing data doesn't break):

```typescript
export interface SessionSummary {
  id?: string;
  createdAt?: string;   // ISO 8601 timestamp
  filename: string;
  // ... rest unchanged
}
```

**Step 2: Commit**

```bash
git add lib/types.ts
git commit -m "feat: add createdAt field to SessionSummary type"
```

---

### Task 2: Set `createdAt` when saving sessions

**Files:**
- Modify: `lib/db.ts:53-73` (saveSession function)

**Step 1: Set createdAt in saveSession**

In `saveSession`, add `createdAt` to the summary before saving:

```typescript
export async function saveSession(
  summary: SessionSummary,
  claims: ValidatedClaim[],
  warnings: string[]
): Promise<string> {
  ensureDir();
  const id = crypto.randomUUID();
  const summaryWithId = { ...summary, id, createdAt: new Date().toISOString() };
  // ... rest unchanged (already uses summaryWithId)
}
```

**Step 2: Commit**

```bash
git add lib/db.ts
git commit -m "feat: stamp createdAt on new sessions"
```

---

### Task 3: Remove session limits

**Files:**
- Modify: `lib/db.ts:103-105` (getDashboardSessions)
- Modify: `app/dashboard/page.tsx:19`

**Step 1: Remove `.slice(0, 50)` in getDashboardSessions**

```typescript
export async function getDashboardSessions(): Promise<SessionSummary[]> {
  return readIndex();
}
```

**Step 2: Remove `.slice(0, 10)` in page.tsx**

Delete line 19: `sessions = sessions.slice(0, 10);`

**Step 3: Verify dashboard still loads**

Run the dev server and confirm the dashboard renders all sessions.

**Step 4: Commit**

```bash
git add lib/db.ts app/dashboard/page.tsx
git commit -m "feat: remove session limits from dashboard"
```

---

### Task 4: Build grouped DashboardTable

**Files:**
- Modify: `components/DashboardTable.tsx` (full rewrite of component body)

This is the main change. The component receives `sessions: SessionSummary[]` and must:

1. Show a segmented control: Day | Week | Month (default: Month)
2. Group sessions by the selected period using `createdAt`
3. Render each group as a collapsible section with a header showing period + count
4. Sessions without `createdAt` go into an "Older" group at the bottom

**Step 1: Add grouping utility functions inside the component file**

```typescript
type GroupMode = 'day' | 'week' | 'month';

function getGroupKey(dateStr: string | undefined, mode: GroupMode): string {
  if (!dateStr) return 'Older';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return 'Older';

  if (mode === 'day') {
    return d.toLocaleDateString('en-ZA', { day: 'numeric', month: 'long', year: 'numeric' });
  }
  if (mode === 'week') {
    // Get Monday of the week
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    const monday = new Date(d);
    monday.setDate(diff);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    return `${monday.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })} – ${sunday.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })}`;
  }
  // month
  return d.toLocaleDateString('en-ZA', { month: 'long', year: 'numeric' });
}

function groupSessions(sessions: SessionSummary[], mode: GroupMode): Map<string, SessionSummary[]> {
  const groups = new Map<string, SessionSummary[]>();
  for (const s of sessions) {
    const key = getGroupKey(s.createdAt, mode);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(s);
  }
  return groups;
}
```

**Step 2: Add the segmented control and collapsible groups**

Replace the component body. The segmented control uses three buttons styled to match the navy theme. Each group is a `<details open>` element (native HTML collapsible, no extra state needed).

```tsx
export default function DashboardTable({ sessions }: { sessions: SessionSummary[] }) {
  const router = useRouter();
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [mode, setMode] = useState<GroupMode>('month');

  // ... keep existing handleRowClick unchanged ...

  if (sessions.length === 0) {
    return (
      <p className="text-gray-400 py-8 text-center text-sm">
        No sessions yet — upload a claim file to get started.
      </p>
    );
  }

  const grouped = groupSessions(sessions, mode);
  const modes: { value: GroupMode; label: string }[] = [
    { value: 'day', label: 'Day' },
    { value: 'week', label: 'Week' },
    { value: 'month', label: 'Month' },
  ];

  return (
    <div>
      {/* Segmented control */}
      <div className="flex gap-1 mb-4 bg-slate-100 rounded-lg p-1 w-fit">
        {modes.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setMode(value)}
            className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              mode === value
                ? 'bg-[#1a3a6b] text-white shadow-sm'
                : 'text-slate-600 hover:text-[#1a3a6b]'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Grouped sessions */}
      {Array.from(grouped.entries()).map(([groupLabel, groupSessions]) => (
        <details key={groupLabel} open className="mb-2">
          <summary className="cursor-pointer flex items-center gap-2 py-2 px-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors select-none">
            <svg className="w-3 h-3 text-slate-400 transition-transform details-open:rotate-90" fill="currentColor" viewBox="0 0 20 20">
              <path d="M6 4l8 6-8 6V4z" />
            </svg>
            <span className="text-xs font-bold text-[#1a3a6b] uppercase tracking-wide">{groupLabel}</span>
            <span className="text-xs text-slate-400">({groupSessions.length})</span>
          </summary>

          <table className="w-full text-sm mt-1">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left pb-3 pr-4 text-xs font-semibold uppercase tracking-wide text-[#1a3a6b]">File</th>
                <th className="text-left pb-3 pr-4 text-xs font-semibold uppercase tracking-wide text-[#1a3a6b]">System</th>
                <th className="text-right pb-3 pr-4 text-xs font-semibold uppercase tracking-wide text-[#1a3a6b]">Total</th>
                <th className="pb-3 text-xs font-semibold uppercase tracking-wide text-[#1a3a6b]">Outcomes</th>
              </tr>
            </thead>
            <tbody>
              {/* ... existing row rendering, identical to current ... */}
            </tbody>
          </table>
        </details>
      ))}
    </div>
  );
}
```

**Step 3: Verify the `details-open:rotate-90` utility works**

Tailwind v4 supports the `open` variant natively. The chevron should rotate when a group is expanded. If not, fall back to `[open]>summary svg { transform: rotate(90deg) }` in the component.

**Step 4: Commit**

```bash
git add components/DashboardTable.tsx
git commit -m "feat: group dashboard sessions by day/week/month with segmented control"
```

---

### Task 5: Update dashboard page heading

**Files:**
- Modify: `app/dashboard/page.tsx:97`

**Step 1: Change "Recent Batches" to "All Batches"**

```tsx
<h2 className="text-sm font-bold text-[#1a3a6b] uppercase tracking-widest mb-4">All Batches</h2>
```

**Step 2: Commit**

```bash
git add app/dashboard/page.tsx
git commit -m "chore: rename dashboard heading to All Batches"
```

---

### Task 6: Verify nothing is broken

**Step 1: Check the API route**

`app/api/dashboard/route.ts` calls `getDashboardSessions()` which now returns all sessions. The API response shape is unchanged (`{ sessions: SessionSummary[] }`). No breaking change.

**Step 2: Check the review page**

`app/review/page.tsx` creates `SessionSummary` objects when exporting — the `createdAt` field is optional so this still works. When it PATCHes via `/api/sessions/{id}`, the `updateSession` function in `db.ts` replaces the full summary in the index. The `createdAt` that was set during `saveSession` is preserved because the review page spreads the existing summary: `{ ...summary, ... }`.

**Step 3: Check the validate route**

`app/api/validate/route.ts` constructs a `SessionSummary` without `createdAt` — that's fine because `saveSession` now adds it.

**Step 4: Manual test checklist**

- [ ] Upload a new CSV → verify session appears on dashboard with today's date group
- [ ] Switch between Day/Week/Month → groups re-sort correctly
- [ ] Collapse and expand groups → chevron rotates, rows hide/show
- [ ] Click a session row → navigates to review page (existing behaviour)
- [ ] Sessions from before this change → appear under "Older" group
- [ ] Dashboard KPIs → still show correct totals (uses `getDashboardStats` which reads all sessions)

**Step 5: Commit (if any fixes needed)**

---

### Touch-point safety summary

| File | Change | Risk |
|------|--------|------|
| `lib/types.ts` | Add optional `createdAt` | None — optional field, no existing code breaks |
| `lib/db.ts` | Set `createdAt` in saveSession, remove slice in getDashboardSessions | Low — additive change + limit removal |
| `app/dashboard/page.tsx` | Remove `.slice(0,10)`, rename heading | None — just removes a filter |
| `components/DashboardTable.tsx` | Add grouping logic + segmented control | Medium — main UI change, but isolated to this component |
| `app/api/dashboard/route.ts` | No change needed | None — inherits from getDashboardSessions |
| `app/api/validate/route.ts` | No change needed | None — saveSession adds createdAt |
| `app/review/page.tsx` | No change needed | None — createdAt preserved through spread |
