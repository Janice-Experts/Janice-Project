# Paediatric ICD Rules Expansion — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand age-based ICD validation with adult-on-child warnings, infant liveborn errors, and broader paediatric-on-adult warnings.

**Architecture:** Add lookup arrays for each age band to the existing demographics validator. Mirror all changes in client-revalidate.ts. Three new issue codes: `DEMO_AGE_INFANT`, `DEMO_AGE_CHILD`, `DEMO_AGE_ADULT_ONLY`. Existing `DEMO_AGE_PAEDIATRIC` expanded.

**Tech Stack:** TypeScript, existing validator engine, existing client-revalidate module.

**Design doc:** `docs/plans/2026-04-05-paediatric-rules-design.md`

---

### Task 1: Add new age rules to server-side demographics validator

**Files:**
- Modify: `ICDGuard/lib/validators/demographics.ts`

**Step 1: Add the new lookup arrays after the existing ones (after line 21)**

Add these arrays after the existing `PAEDIATRIC_ONLY_PREFIXES`:

```ts
// Liveborn infant codes — error if patient > 1 year old
const INFANT_ONLY_PREFIXES = ['Z38'];

// Adult degenerative conditions — warning if patient < 12 years old
const ADULT_OVER_12_PREFIXES = [
  'M15', 'M16', 'M17', 'M18', 'M19',  // Osteoarthritis
  'M80', 'M81',                          // Osteoporosis
  'I70',                                  // Atherosclerosis
  'E11',                                  // Type 2 diabetes
];

// Adult-only conditions — warning if patient < 18 years old
const ADULT_OVER_18_PREFIXES = [
  'G20',                                  // Parkinson's
  'G30',                                  // Alzheimer's
  'F00', 'F01', 'F02', 'F03',            // Dementia
  'R54',                                  // Senility
  'N95',                                  // Menopausal disorders
  'N40',                                  // Prostatic hyperplasia
  'N41',                                  // Prostatitis
  'C61',                                  // Prostate cancer
];
```

**Step 2: Add helper functions**

Add these after the existing `isPaediatricOnly` function:

```ts
function isInfantOnly(code: string): boolean {
  const u = code.toUpperCase();
  return INFANT_ONLY_PREFIXES.some((p) => u.startsWith(p));
}

function isAdultOver12(code: string): boolean {
  const u = code.toUpperCase();
  return ADULT_OVER_12_PREFIXES.some((p) => u.startsWith(p));
}

function isAdultOver18(code: string): boolean {
  const u = code.toUpperCase();
  return ADULT_OVER_18_PREFIXES.some((p) => u.startsWith(p));
}
```

**Step 3: Add the new rules inside the validator loop**

Add these blocks after the existing paediatric check (after line 96), still inside the `for (const claim of claims)` loop:

```ts
    // Infant-only check (Z38 liveborn codes) — error if age > 1 year
    if (claim.dob && claim.serviceDate && isInfantOnly(rawCode)) {
      const ageInDays = getAgeInDays(claim.dob, claim.serviceDate);
      if (ageInDays !== null && ageInDays > 365) {
        issues.push({
          field: 'icdCode',
          code: 'DEMO_AGE_INFANT',
          message: `ICD code "${rawCode}" is a liveborn infant code — patient is ${Math.floor(ageInDays / 365.25)} years old`,
          severity: 'error',
        });
      }
    }

    // Adult degenerative codes on children under 12 — warning
    if (claim.dob && claim.serviceDate && isAdultOver12(rawCode)) {
      const ageInDays = getAgeInDays(claim.dob, claim.serviceDate);
      if (ageInDays !== null && Math.floor(ageInDays / 365.25) < 12) {
        issues.push({
          field: 'icdCode',
          code: 'DEMO_AGE_CHILD',
          message: `ICD code "${rawCode}" is an adult condition — patient is only ${Math.floor(ageInDays / 365.25)} years old`,
          severity: 'warning',
        });
      }
    }

    // Adult-only codes on patients under 18 — warning
    if (claim.dob && claim.serviceDate && isAdultOver18(rawCode)) {
      const ageInDays = getAgeInDays(claim.dob, claim.serviceDate);
      if (ageInDays !== null && Math.floor(ageInDays / 365.25) < 18) {
        issues.push({
          field: 'icdCode',
          code: 'DEMO_AGE_ADULT_ONLY',
          message: `ICD code "${rawCode}" is typically for adults only — patient is ${Math.floor(ageInDays / 365.25)} years old`,
          severity: 'warning',
        });
      }
    }
```

**Step 4: Expand the existing PAEDIATRIC_ONLY_PREFIXES**

Update line 21 to include Z38:

```ts
const PAEDIATRIC_ONLY_PREFIXES = ['Z00.1', 'Z00.2', 'Z00.3', 'Z76.1', 'Z76.2', 'Z38'];
```

**Step 5: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 6: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add lib/validators/demographics.ts && git commit -m "feat: expand paediatric age rules in demographics validator"
```

---

### Task 2: Mirror new rules in client-side revalidation

**Files:**
- Modify: `ICDGuard/lib/client-revalidate.ts`

**Step 1: Add the same lookup arrays**

After the existing `PAEDIATRIC_ONLY_PREFIXES` (line 17), add the same arrays:

```ts
const INFANT_ONLY_PREFIXES = ['Z38'];

const ADULT_OVER_12_PREFIXES = [
  'M15', 'M16', 'M17', 'M18', 'M19',
  'M80', 'M81',
  'I70',
  'E11',
];

const ADULT_OVER_18_PREFIXES = [
  'G20',
  'G30',
  'F00', 'F01', 'F02', 'F03',
  'R54',
  'N95',
  'N40', 'N41',
  'C61',
];
```

Also update the existing `PAEDIATRIC_ONLY_PREFIXES` to include `'Z38'`.

**Step 2: Add the new validation blocks**

After the existing paediatric check (around line 169), add the same three blocks as in the server validator (infant-only, adult-over-12, adult-over-18). Use `icdRaw` instead of `rawCode` (that's the variable name in client-revalidate.ts).

```ts
    // Infant-only check (Z38 liveborn codes) — error if age > 1 year
    if (claim.dob && claim.serviceDate && INFANT_ONLY_PREFIXES.some((p) => icdRaw.toUpperCase().startsWith(p))) {
      const ageInDays = getAgeInDays(claim.dob, claim.serviceDate);
      if (ageInDays !== null && ageInDays > 365) {
        issues.push({
          field: 'icdCode',
          code: 'DEMO_AGE_INFANT',
          message: `ICD code "${icdRaw}" is a liveborn infant code — patient is ${Math.floor(ageInDays / 365.25)} years old`,
          severity: 'error',
        });
      }
    }

    // Adult degenerative codes on children under 12 — warning
    if (claim.dob && claim.serviceDate && ADULT_OVER_12_PREFIXES.some((p) => icdRaw.toUpperCase().startsWith(p))) {
      const ageInDays = getAgeInDays(claim.dob, claim.serviceDate);
      if (ageInDays !== null && Math.floor(ageInDays / 365.25) < 12) {
        issues.push({
          field: 'icdCode',
          code: 'DEMO_AGE_CHILD',
          message: `ICD code "${icdRaw}" is an adult condition — patient is only ${Math.floor(ageInDays / 365.25)} years old`,
          severity: 'warning',
        });
      }
    }

    // Adult-only codes on patients under 18 — warning
    if (claim.dob && claim.serviceDate && ADULT_OVER_18_PREFIXES.some((p) => icdRaw.toUpperCase().startsWith(p))) {
      const ageInDays = getAgeInDays(claim.dob, claim.serviceDate);
      if (ageInDays !== null && Math.floor(ageInDays / 365.25) < 18) {
        issues.push({
          field: 'icdCode',
          code: 'DEMO_AGE_ADULT_ONLY',
          message: `ICD code "${icdRaw}" is typically for adults only — patient is ${Math.floor(ageInDays / 365.25)} years old`,
          severity: 'warning',
        });
      }
    }
```

**Step 3: Add new issue codes to recheckedCodes set**

Find the `recheckedCodes` set (around line 318-325) and add the new codes:

```ts
'DEMO_GENDER_MISMATCH', 'DEMO_AGE_NEONATAL', 'DEMO_AGE_PAEDIATRIC',
'DEMO_AGE_INFANT', 'DEMO_AGE_CHILD', 'DEMO_AGE_ADULT_ONLY',
```

**Step 4: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 5: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add lib/client-revalidate.ts && git commit -m "feat: mirror paediatric age rules in client-side revalidation"
```

---

### Task 3: Smoke test

**No files changed — verification only.**

**Step 1:** Dev server should be running at `http://localhost:3000`

**Step 2: Test with a CSV that has paediatric claims**

Create a test scenario with these claims (or use an existing test CSV and modify):
- Patient DOB = 2020-01-01 (6 years old), ICD = M17.1 (osteoarthritis knee) → should get DEMO_AGE_CHILD warning
- Patient DOB = 2010-01-01 (16 years old), ICD = G30.0 (Alzheimer's) → should get DEMO_AGE_ADULT_ONLY warning
- Patient DOB = 2025-01-01 (1.25 years old), ICD = Z38.0 (liveborn infant) → should get DEMO_AGE_INFANT error
- Patient DOB = 1970-01-01 (56 years old), ICD = Z00.1 (child health exam) → should get DEMO_AGE_PAEDIATRIC warning
- Patient DOB = 2024-01-01 (2 years old), ICD = P01.0 (neonatal) → should get DEMO_AGE_NEONATAL error (existing rule)

**Step 3: Verify client-side revalidation**

- On the review page, correct an ICD code to an adult-only code for a child patient
- Verify the warning appears immediately after correction (client-side revalidation)

**Step 4:** If any fixes needed, commit them.

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Server-side age rules | `lib/validators/demographics.ts` (modify) |
| 2 | Client-side mirror | `lib/client-revalidate.ts` (modify) |
| 3 | Smoke test | — |
