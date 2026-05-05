# Learned Tariff Substitutions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** ICDGuard learns common tariff-code corrections (A → B) from accumulated user data and surfaces soft warnings on future uploads.

**Architecture:** Mine the existing `claims.corrected_tariff_code` data. Aggregate per `(original → corrected)` pair into a new `tariff_substitution_rules` table, updated eagerly when the user saves corrections. A new validator emits an `info`-severity issue when a rule's volume + dominance thresholds are met. UI renders the hint distinctly from errors/warnings; dismissals are tracked but unused in v1.

**Tech Stack:** Next.js 16 (App Router), TypeScript, @vercel/postgres (Neon), file-based DB fallback for local dev. Vitest added for new tests.

**Design doc:** `docs/plans/2026-05-05-learned-tariff-substitutions-design.md`

---

## Decisions baked in

- **Thresholds (initial)**: `count >= 10` AND `count / total_seen >= 0.70`. Tunable later.
- **No worktree** — work directly on `main` (per `memory/feedback_no_worktrees.md`).
- **Test framework**: project has no tests today. This plan adds **vitest** as the first task. ~3 lines of `package.json` + one tiny config file. If you'd rather skip tests entirely (matching current codebase conventions), drop Task 1 and remove the test steps from later tasks.
- **Severity tier**: extend `ValidationSeverity` with a new `'info'` value. The status calculation in `engine.ts` is unchanged — `info` issues never downgrade `valid` to `needs_review`.
- **Correction-recording hook**: in `updateSession`. Compute the diff between previous and new `corrected_tariff_code` per claim line; only count deltas (not every save).

---

## Task 1: Add vitest

**Files:**
- Modify: `ICDGuard/package.json`
- Create: `ICDGuard/vitest.config.ts`

**Step 1: Install vitest**

```bash
cd ICDGuard && npm install --save-dev vitest @vitest/coverage-v8
```

**Step 2: Add test script to `package.json`**

In the `scripts` block, add:

```json
"test": "vitest run",
"test:watch": "vitest"
```

**Step 3: Create `vitest.config.ts`**

```ts
import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    environment: 'node',
    globals: false,
    include: ['lib/**/*.test.ts', 'tests/**/*.test.ts'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
    },
  },
});
```

**Step 4: Verify**

Run: `cd ICDGuard && npm test`
Expected: `No test files found` (vitest exits cleanly with code 0 or 1; no errors).

**Step 5: Commit**

```bash
git add ICDGuard/package.json ICDGuard/package-lock.json ICDGuard/vitest.config.ts
git commit -m "chore: add vitest for unit testing"
```

---

## Task 2: Add `info` severity tier

**Files:**
- Modify: `ICDGuard/lib/types.ts:2`
- Modify: `ICDGuard/lib/validators/engine.ts:21-29` and `:32-58`

**Step 1: Write failing test**

Create `ICDGuard/lib/validators/engine.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { runValidators, countByCategory, registerValidator } from './engine';
import { ClaimRow, ValidationIssue } from '@/lib/types';

describe('engine severity handling', () => {
  it('does not downgrade status for info-only issues', async () => {
    registerValidator(async () => {
      const m = new Map<string, ValidationIssue[]>();
      m.set('c1', [{ field: 'tariffCode', code: 'LEARNED_SUBSTITUTION', message: 'hint', severity: 'info' }]);
      return m;
    });
    const claims: ClaimRow[] = [
      { id: 'c1', raw: {}, corrections: {} },
    ];
    const results = await runValidators(claims);
    expect(results[0].status).toBe('valid');
  });

  it('counts LEARNED_ codes under "learned" category', () => {
    const counts = countByCategory([
      {
        claimId: 'c1',
        status: 'valid',
        issues: [{ field: 'tariffCode', code: 'LEARNED_SUBSTITUTION', message: 'x', severity: 'info' }],
      },
    ]);
    expect(counts.learned).toBe(1);
  });
});
```

**Step 2: Run — verify it fails**

Run: `cd ICDGuard && npm test`
Expected: FAIL — second test fails because `learned` is not yet a category; first may pass coincidentally.

**Step 3: Update `lib/types.ts:2`**

```ts
export type ValidationSeverity = 'error' | 'warning' | 'info';
```

**Step 4: Update `lib/validators/engine.ts`**

In `runValidators` (lines 21-29), the existing logic already handles `info` correctly because `info` is neither `'error'` nor `'warning'` — status falls through to `'valid'`. No code change needed here, but **verify by reading the current logic** and confirm.

In `countByCategory` (lines 32-58), add a `learned` bucket:

```ts
const counts: Record<string, number> = {
  icd: 0,
  tariff: 0,
  treatment: 0,
  duplicate: 0,
  completeness: 0,
  demographics: 0,
  dates: 0,
  pmb: 0,
  learned: 0,
};
```

And add this branch in the inner loop (before the final `}`):

```ts
else if (issue.code.startsWith('LEARNED_')) counts.learned++;
```

**Step 5: Run tests — verify pass**

Run: `cd ICDGuard && npm test`
Expected: PASS for both engine tests.

**Step 6: Commit**

```bash
git add ICDGuard/lib/types.ts ICDGuard/lib/validators/engine.ts ICDGuard/lib/validators/engine.test.ts
git commit -m "feat: add info severity tier and learned issue category"
```

---

## Task 3: Migration — `tariff_substitution_rules` table

**Files:**
- Create: `ICDGuard/scripts/migrations/003-tariff-substitution-rules.sql`

**Step 1: Write the migration**

```sql
CREATE TABLE IF NOT EXISTS tariff_substitution_rules (
  original         TEXT NOT NULL,
  corrected        TEXT NOT NULL,
  count            INT NOT NULL DEFAULT 0,
  dismissed_count  INT NOT NULL DEFAULT 0,
  last_seen        TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (original, corrected)
);
CREATE INDEX IF NOT EXISTS idx_tariff_sub_rules_original ON tariff_substitution_rules (original);
```

**Step 2: Apply to local Postgres (if available) or note for prod**

If running with `POSTGRES_URL` set locally, apply via your usual migration runner (whatever `seed:db` does). Otherwise, note that the migration must be applied to the Neon/Vercel Postgres instance manually before deploy. **Do not** auto-apply migrations on app startup.

**Step 3: Commit**

```bash
git add ICDGuard/scripts/migrations/003-tariff-substitution-rules.sql
git commit -m "feat: migration for tariff substitution rules table"
```

---

## Task 4: Postgres DB layer

**Files:**
- Modify: `ICDGuard/lib/db-postgres.ts` (append new functions)

**Step 1: Write failing test**

Create `ICDGuard/lib/db-postgres.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import type { LearnedTariffRule } from '@/lib/types';

describe('learned-rules DB layer (postgres)', () => {
  it('exports the expected functions', async () => {
    const mod = await import('@/lib/db-postgres');
    expect(typeof mod.recordTariffCorrection).toBe('function');
    expect(typeof mod.recordTariffDismissal).toBe('function');
    expect(typeof mod.getLearnedTariffRules).toBe('function');
  });
});
```

(We can't easily unit-test the SQL itself without a DB; this is a smoke test for the export shape. Real verification happens in the smoke test at the end.)

**Step 2: Add `LearnedTariffRule` type to `lib/types.ts`**

Append to `ICDGuard/lib/types.ts`:

```ts
export interface LearnedTariffRule {
  original: string;
  corrected: string;
  count: number;
  totalSeen: number;
  dominance: number;       // 0..1
  dismissedCount: number;
  lastSeen: string;        // ISO timestamp
}
```

**Step 3: Run test — verify fails**

Run: `cd ICDGuard && npm test`
Expected: FAIL — functions don't exist on `db-postgres`.

**Step 4: Append functions to `lib/db-postgres.ts`**

```ts
// ---------------------------------------------------------------------------
// Learned tariff substitution rules
// ---------------------------------------------------------------------------

import type { LearnedTariffRule } from '@/lib/types';

export async function recordTariffCorrection(
  original: string,
  corrected: string
): Promise<void> {
  if (!original || !corrected || original === corrected) return;
  await sql`
    INSERT INTO tariff_substitution_rules (original, corrected, count, last_seen)
    VALUES (${original}, ${corrected}, 1, now())
    ON CONFLICT (original, corrected)
    DO UPDATE SET count = tariff_substitution_rules.count + 1,
                  last_seen = now()`;
}

export async function recordTariffDismissal(
  original: string,
  corrected: string
): Promise<void> {
  if (!original || !corrected) return;
  await sql`
    UPDATE tariff_substitution_rules
       SET dismissed_count = dismissed_count + 1
     WHERE original = ${original} AND corrected = ${corrected}`;
}

export async function getLearnedTariffRules(
  minCount = 10,
  minDominance = 0.7
): Promise<LearnedTariffRule[]> {
  const { rows } = await sql`
    SELECT
      original,
      corrected,
      count,
      SUM(count) OVER (PARTITION BY original) AS total_seen,
      dismissed_count,
      last_seen
    FROM tariff_substitution_rules
    ORDER BY count DESC`;
  return rows
    .map((r) => {
      const total = Number(r.total_seen);
      const cnt = Number(r.count);
      return {
        original: r.original as string,
        corrected: r.corrected as string,
        count: cnt,
        totalSeen: total,
        dominance: total > 0 ? cnt / total : 0,
        dismissedCount: Number(r.dismissed_count),
        lastSeen: new Date(r.last_seen as string).toISOString(),
      };
    })
    .filter((r) => r.count >= minCount && r.dominance >= minDominance);
}
```

(Remove the duplicate `import type { LearnedTariffRule } …` if it conflicts with an existing import. The block above assumes the file's existing imports are at the top — merge accordingly.)

**Step 5: Run test — verify passes**

Run: `cd ICDGuard && npm test`
Expected: PASS.

**Step 6: Commit**

```bash
git add ICDGuard/lib/db-postgres.ts ICDGuard/lib/types.ts ICDGuard/lib/db-postgres.test.ts
git commit -m "feat: postgres layer for learned tariff rules"
```

---

## Task 5: File-based DB layer

**Files:**
- Modify: `ICDGuard/lib/db-file.ts`

**Step 1: Add storage**

Local dev uses a single JSON file: `data/learned-tariff-rules.json`. Append the following to `lib/db-file.ts`:

```ts
import type { LearnedTariffRule } from '@/lib/types';

const RULES_FILE = path.join(DATA_DIR, 'learned-tariff-rules.json');

interface RuleRow {
  original: string;
  corrected: string;
  count: number;
  dismissed_count: number;
  last_seen: string;
}

function readRules(): RuleRow[] {
  try {
    if (!fs.existsSync(RULES_FILE)) return [];
    return JSON.parse(fs.readFileSync(RULES_FILE, 'utf-8'));
  } catch {
    return [];
  }
}

function writeRules(rows: RuleRow[]): void {
  ensureDir();
  fs.writeFileSync(RULES_FILE, JSON.stringify(rows, null, 2));
}

export async function recordTariffCorrection(
  original: string,
  corrected: string
): Promise<void> {
  if (!original || !corrected || original === corrected) return;
  const rows = readRules();
  const existing = rows.find((r) => r.original === original && r.corrected === corrected);
  if (existing) {
    existing.count += 1;
    existing.last_seen = new Date().toISOString();
  } else {
    rows.push({
      original,
      corrected,
      count: 1,
      dismissed_count: 0,
      last_seen: new Date().toISOString(),
    });
  }
  writeRules(rows);
}

export async function recordTariffDismissal(
  original: string,
  corrected: string
): Promise<void> {
  if (!original || !corrected) return;
  const rows = readRules();
  const existing = rows.find((r) => r.original === original && r.corrected === corrected);
  if (!existing) return;
  existing.dismissed_count += 1;
  writeRules(rows);
}

export async function getLearnedTariffRules(
  minCount = 10,
  minDominance = 0.7
): Promise<LearnedTariffRule[]> {
  const rows = readRules();
  const totalsByOriginal = new Map<string, number>();
  for (const r of rows) {
    totalsByOriginal.set(r.original, (totalsByOriginal.get(r.original) ?? 0) + r.count);
  }
  return rows
    .map((r) => {
      const total = totalsByOriginal.get(r.original) ?? 0;
      return {
        original: r.original,
        corrected: r.corrected,
        count: r.count,
        totalSeen: total,
        dominance: total > 0 ? r.count / total : 0,
        dismissedCount: r.dismissed_count,
        lastSeen: r.last_seen,
      };
    })
    .filter((r) => r.count >= minCount && r.dominance >= minDominance);
}
```

**Step 2: Write a unit test for the file-based path (it doesn't need a DB)**

Create `ICDGuard/lib/db-file.test.ts`:

```ts
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

const TMP = path.join(process.cwd(), 'data');
const RULES = path.join(TMP, 'learned-tariff-rules.json');

describe('learned-rules file DB layer', () => {
  beforeEach(() => {
    if (fs.existsSync(RULES)) fs.unlinkSync(RULES);
  });
  afterEach(() => {
    if (fs.existsSync(RULES)) fs.unlinkSync(RULES);
  });

  it('records, queries, and applies thresholds correctly', async () => {
    const m = await import('@/lib/db-file');
    // Below thresholds: 9 corrections of 0190 → 0191
    for (let i = 0; i < 9; i++) await m.recordTariffCorrection('0190', '0191');
    expect((await m.getLearnedTariffRules()).length).toBe(0);

    // Hit volume threshold (10) — dominance is 100%
    await m.recordTariffCorrection('0190', '0191');
    const rules = await m.getLearnedTariffRules();
    expect(rules).toHaveLength(1);
    expect(rules[0].original).toBe('0190');
    expect(rules[0].corrected).toBe('0191');
    expect(rules[0].count).toBe(10);
    expect(rules[0].dominance).toBeCloseTo(1.0);
  });

  it('filters out low-dominance pairs', async () => {
    const m = await import('@/lib/db-file');
    // 8 to 0191, 7 to 0192 — total 15, top is 8/15 = 0.53 < 0.70
    for (let i = 0; i < 8; i++) await m.recordTariffCorrection('0200', '0191');
    for (let i = 0; i < 7; i++) await m.recordTariffCorrection('0200', '0192');
    expect(await m.getLearnedTariffRules()).toHaveLength(0);
  });
});
```

**Step 3: Run — verify pass**

Run: `cd ICDGuard && npm test`
Expected: PASS for both new file-DB tests.

**Step 4: Commit**

```bash
git add ICDGuard/lib/db-file.ts ICDGuard/lib/db-file.test.ts
git commit -m "feat: file-based DB layer for learned tariff rules"
```

---

## Task 6: DB router (`lib/db.ts`)

**Files:**
- Modify: `ICDGuard/lib/db.ts`

**Step 1: Append router functions**

```ts
import type { LearnedTariffRule } from '@/lib/types';

export async function recordTariffCorrection(original: string, corrected: string): Promise<void> {
  const mod = usePostgres ? await pg() : await file();
  return mod.recordTariffCorrection(original, corrected);
}

export async function recordTariffDismissal(original: string, corrected: string): Promise<void> {
  const mod = usePostgres ? await pg() : await file();
  return mod.recordTariffDismissal(original, corrected);
}

export async function getLearnedTariffRules(): Promise<LearnedTariffRule[]> {
  const mod = usePostgres ? await pg() : await file();
  return mod.getLearnedTariffRules();
}
```

**Step 2: Verify type-check**

Run: `cd ICDGuard && npx tsc --noEmit`
Expected: No errors.

**Step 3: Commit**

```bash
git add ICDGuard/lib/db.ts
git commit -m "feat: db router exposes learned-rule functions"
```

---

## Task 7: Hook `updateSession` to record correction deltas

**Goal:** When a user saves corrections, record only newly-applied tariff corrections (not every save). The diff is computed against what's already stored.

**Files:**
- Modify: `ICDGuard/lib/db-postgres.ts` — `updateSession` function (`:116-150`)
- Modify: `ICDGuard/lib/db-file.ts` — `updateSession` function (`:51-65`)

**Step 1: Update Postgres `updateSession`**

Before the `DELETE FROM claims …` line, add:

```ts
// Pull existing correction state so we can record only newly-applied corrections.
const { rows: existingRows } = await sql`
  SELECT line_number, tariff_code, corrected_tariff_code
    FROM claims WHERE session_id = ${sessionId}`;
const existingByLine = new Map<number, { tariff: string | null; corrected: string | null }>();
for (const r of existingRows) {
  existingByLine.set(Number(r.line_number), {
    tariff: r.tariff_code as string | null,
    corrected: r.corrected_tariff_code as string | null,
  });
}
```

After `await insertClaims(sessionId, claims);`, add:

```ts
// Record correction deltas
for (let i = 0; i < claims.length; i++) {
  const c = claims[i];
  const newCorrected = c.corrections?.tariffCode ?? null;
  const original = c.tariffCode ?? null;
  const prev = existingByLine.get(i);
  const prevCorrected = prev?.corrected ?? null;

  if (
    original &&
    newCorrected &&
    newCorrected !== original &&
    newCorrected !== prevCorrected
  ) {
    await recordTariffCorrection(original, newCorrected);
  }
}
```

(Reference `recordTariffCorrection` from the same module — already defined in Task 4.)

**Step 2: Update file-based `updateSession`**

Same diff logic, comparing `existing.claims` (already loaded at `:59`) with the new `claims`. Replace the body of `updateSession`:

```ts
const sessionFile = path.join(DATA_DIR, `${id}.json`);
if (!fs.existsSync(sessionFile)) return;

const existing: SessionData = JSON.parse(fs.readFileSync(sessionFile, 'utf-8'));
const existingByIndex = new Map<number, { tariff?: string; corrected?: string }>();
existing.claims.forEach((c, idx) =>
  existingByIndex.set(idx, { tariff: c.tariffCode, corrected: c.corrections?.tariffCode })
);

fs.writeFileSync(sessionFile, JSON.stringify({ ...existing, claims, summary }));

const index = readIndex();
const idx = index.findIndex((s) => s.id === id);
if (idx !== -1) { index[idx] = { ...summary, createdAt: index[idx].createdAt }; writeIndex(index); }

for (let i = 0; i < claims.length; i++) {
  const c = claims[i];
  const newCorrected = c.corrections?.tariffCode;
  const original = c.tariffCode;
  const prev = existingByIndex.get(i);
  const prevCorrected = prev?.corrected;

  if (
    original &&
    newCorrected &&
    newCorrected !== original &&
    newCorrected !== prevCorrected
  ) {
    await recordTariffCorrection(original, newCorrected);
  }
}
```

**Step 3: Write a behavioural test**

Create `ICDGuard/lib/db-file-update.test.ts`:

```ts
import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import * as db from '@/lib/db-file';
import type { ValidatedClaim, SessionSummary } from '@/lib/types';

const DATA = path.join(process.cwd(), 'data');

describe('updateSession records correction deltas', () => {
  beforeEach(() => {
    // Clean slate
    if (fs.existsSync(DATA)) fs.rmSync(DATA, { recursive: true, force: true });
  });

  it('records a tariff correction once, not on subsequent re-saves', async () => {
    const claims: ValidatedClaim[] = [
      {
        id: '1',
        tariffCode: '0190',
        raw: {},
        corrections: {},
        result: { claimId: '1', status: 'valid', issues: [] },
      },
    ];
    const summary: SessionSummary = {
      filename: 'x.csv', sourceSystem: 'goodx',
      total: 1, valid: 1, needsReview: 0, rejected: 0, passRate: 1,
      errorBreakdown: { icd: 0, tariff: 0, treatment: 0, duplicate: 0, completeness: 0, demographics: 0, dates: 0, pmb: 0 },
    };
    const id = await db.saveSession(summary, claims, []);

    // Apply correction
    claims[0].corrections.tariffCode = '0191';
    await db.updateSession(id, claims, summary);
    let rules = await db.getLearnedTariffRules(1, 0); // lower thresholds for visibility
    expect(rules[0]?.count).toBe(1);

    // Re-save with same correction — should NOT increment
    await db.updateSession(id, claims, summary);
    rules = await db.getLearnedTariffRules(1, 0);
    expect(rules[0]?.count).toBe(1);

    // Change correction — increments new pair
    claims[0].corrections.tariffCode = '0192';
    await db.updateSession(id, claims, summary);
    rules = await db.getLearnedTariffRules(1, 0);
    const for191 = rules.find((r) => r.corrected === '0191');
    const for192 = rules.find((r) => r.corrected === '0192');
    expect(for191?.count).toBe(1);
    expect(for192?.count).toBe(1);
  });
});
```

**Step 4: Run — verify pass**

Run: `cd ICDGuard && npm test`
Expected: PASS.

**Step 5: Commit**

```bash
git add ICDGuard/lib/db-postgres.ts ICDGuard/lib/db-file.ts ICDGuard/lib/db-file-update.test.ts
git commit -m "feat: record tariff correction deltas on session update"
```

---

## Task 8: Validator — `lib/validators/learned.ts`

**Files:**
- Create: `ICDGuard/lib/validators/learned.ts`
- Create: `ICDGuard/lib/validators/learned.test.ts`
- Modify: `ICDGuard/app/api/validate/route.ts:9-18` — add registration import

**Step 1: Write failing test**

`ICDGuard/lib/validators/learned.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { ClaimRow } from '@/lib/types';

vi.mock('@/lib/db', () => ({
  getLearnedTariffRules: vi.fn(async () => [
    { original: '0190', corrected: '0191', count: 47, totalSeen: 58, dominance: 0.81, dismissedCount: 0, lastSeen: '' },
  ]),
}));

describe('learned validator', () => {
  beforeEach(() => vi.clearAllMocks());

  it('emits info-level LEARNED_SUBSTITUTION for matching tariff', async () => {
    const { learnedValidator } = await import('./learned');
    const claims: ClaimRow[] = [
      { id: 'c1', tariffCode: '0190', raw: {}, corrections: {} },
      { id: 'c2', tariffCode: '9999', raw: {}, corrections: {} },
    ];
    const out = await learnedValidator(claims);
    expect(out.get('c1')?.[0].code).toBe('LEARNED_SUBSTITUTION');
    expect(out.get('c1')?.[0].severity).toBe('info');
    expect(out.get('c1')?.[0].suggestedValue).toBe('0191');
    expect(out.has('c2')).toBe(false);
  });

  it('uses corrected tariff if present (does not flag already-corrected lines)', async () => {
    const { learnedValidator } = await import('./learned');
    const claims: ClaimRow[] = [
      { id: 'c1', tariffCode: '0190', raw: {}, corrections: { tariffCode: '0191' } },
    ];
    const out = await learnedValidator(claims);
    expect(out.has('c1')).toBe(false);
  });
});
```

**Step 2: Run — verify fails**

Run: `cd ICDGuard && npm test`
Expected: FAIL — `learnedValidator` not yet defined.

**Step 3: Implement `lib/validators/learned.ts`**

```ts
import { Validator, registerValidator } from './engine';
import { ClaimRow, ValidationIssue } from '@/lib/types';
import { getLearnedTariffRules } from '@/lib/db';

export const learnedValidator: Validator = async (claims: ClaimRow[]) => {
  const results = new Map<string, ValidationIssue[]>();
  const rules = await getLearnedTariffRules();
  if (rules.length === 0) return results;

  const ruleMap = new Map(rules.map((r) => [r.original, r]));

  for (const claim of claims) {
    const tariff = (claim.corrections['tariffCode'] ?? claim.tariffCode ?? '').trim();
    if (!tariff) continue;

    const rule = ruleMap.get(tariff);
    if (!rule) continue;

    const dominancePct = Math.round(rule.dominance * 100);
    results.set(claim.id, [
      {
        field: 'tariffCode',
        code: 'LEARNED_SUBSTITUTION',
        message: `Typically corrected to ${rule.corrected} (${rule.count} of ${rule.totalSeen} times, ${dominancePct}%)`,
        severity: 'info',
        suggestedValue: rule.corrected,
      },
    ]);
  }

  return results;
};

registerValidator(learnedValidator);
```

**Step 4: Wire registration in the validate route**

In `app/api/validate/route.ts:9-18`, add one more side-effect import:

```ts
import '@/lib/validators/learned';
```

**Step 5: Run — verify pass**

Run: `cd ICDGuard && npm test`
Expected: PASS for `learned.test.ts`.

**Step 6: Commit**

```bash
git add ICDGuard/lib/validators/learned.ts ICDGuard/lib/validators/learned.test.ts ICDGuard/app/api/validate/route.ts
git commit -m "feat: learned-substitution validator"
```

---

## Task 9: UI — render info-tier issues distinctly

**Files:**
- Modify: components that render `ValidationIssue` (likely `ICDGuard/components/ClaimCard.tsx` and/or `ICDGuard/components/ClaimGroupCard.tsx` — confirm by grep)

**Step 1: Find issue rendering sites**

Run: `grep -rn "issue.severity" ICDGuard/components ICDGuard/app`

Identify every place severity is branched on for styling. There will likely be 1–3 sites.

**Step 2: Add an `info` style branch**

In each rendering site, add an `info` case alongside `error` and `warning`. Suggested visual:

- **Background**: `bg-blue-50` (or theme equivalent of "informational, not an error")
- **Border / text**: a calm blue, distinct from amber-warning and red-error
- **Icon**: lightbulb (💡) or info circle
- **Label**: "Hint" (vs "Error" / "Warning")

**Step 3: Manual verification**

Run dev server: `cd ICDGuard && npm run dev`
Seed a rule manually in the DB (postgres example):
```sql
INSERT INTO tariff_substitution_rules (original, corrected, count) VALUES ('0190', '0191', 50);
```
Or for file-based: edit `data/learned-tariff-rules.json`.

Upload a claim file containing tariff `0190`. Confirm:
- A blue/info-styled hint appears on the card
- Status remains `valid` (not `needs_review`)
- The hint references `0191` and shows the count/percentage

**Step 4: Commit**

```bash
git add ICDGuard/components/<files>
git commit -m "feat: render info-tier learned hints in claim cards"
```

---

## Task 10: Dismiss API + UI wire

**Files:**
- Create: `ICDGuard/app/api/learned-rules/dismiss/route.ts`
- Modify: the card components from Task 9 to add a "Dismiss" button on info-tier issues

**Step 1: Write the API endpoint**

```ts
import { NextRequest, NextResponse } from 'next/server';
import { recordTariffDismissal } from '@/lib/db';

export async function POST(req: NextRequest) {
  const { original, corrected } = await req.json();
  if (typeof original !== 'string' || typeof corrected !== 'string') {
    return NextResponse.json({ error: 'original and corrected required' }, { status: 400 });
  }
  await recordTariffDismissal(original, corrected);
  return NextResponse.json({ ok: true });
}
```

**Step 2: UI — add Dismiss button**

In the info-tier rendering branch (Task 9), add a `Dismiss` button. On click, POST `{ original: tariffCode, corrected: suggestedValue }` to `/api/learned-rules/dismiss`, then hide the issue locally (no full reload).

**Step 3: Manual verification**

In the seeded scenario from Task 9, click Dismiss. Verify:
- Issue disappears from the UI
- `dismissed_count` increments in DB (`SELECT * FROM tariff_substitution_rules WHERE original='0190'`)

**Step 4: Commit**

```bash
git add ICDGuard/app/api/learned-rules/dismiss/route.ts ICDGuard/components/<files>
git commit -m "feat: dismiss learned-substitution hints"
```

---

## Task 11: End-to-end smoke test

**Goal:** Verify the full loop works against real Postgres (production data path).

**Step 1: Apply migration to prod Postgres**

Connect to Neon/Vercel Postgres and run `scripts/migrations/003-tariff-substitution-rules.sql`.

**Step 2: Verify table exists**

```sql
\d tariff_substitution_rules
```

**Step 3: Deploy to Vercel**

```bash
cd ICDGuard && git push origin main
```
Wait for deploy. Visit `https://icdguard.co.za`.

**Step 4: Exercise the loop**

a. Upload a claim CSV containing tariff `0190`.
b. Open the claim, change tariff `0190` → `0191`, save.
c. Repeat 9 more times (or seed directly via SQL: `UPDATE tariff_substitution_rules SET count = 10 WHERE original='0190' AND corrected='0191';`).
d. Upload a fresh CSV containing `0190`.
e. Verify the info-tier hint appears on the new upload.

**Step 5: Inspect rule state**

```sql
SELECT
  original, corrected, count,
  SUM(count) OVER (PARTITION BY original) AS total_seen,
  ROUND(count::numeric / SUM(count) OVER (PARTITION BY original) * 100, 1) AS dominance_pct,
  dismissed_count, last_seen
FROM tariff_substitution_rules
ORDER BY count DESC;
```

**Step 6: Update memory**

Append a line to `memory/project_feature_backlog.md` under High (Implemented):

```
- Learned tariff substitutions ✅ 2026-05-XX — system mines correction history; surfaces info-tier hints when (count ≥ 10, dominance ≥ 70%) thresholds met. v1: tariff-only, no auth, dismissals tracked but unused.
```

---

## Out of scope (defer to a future plan)

- ICD-conditional learned rules (`tariff + ICD → tariff`)
- ICD substitution learning
- Per-scheme / per-practice scoping
- Decay or rule expiry
- Auto-application of rules
- Dismissal-based rule weakening
- Admin UI for inspecting rules (SQL is enough for v1)
