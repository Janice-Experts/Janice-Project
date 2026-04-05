# Tariff Code Browser — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a browsable tariff code tree with keyword-based categorization, as a third tab on /search and as a modal from the tariff 🔍 button.

**Architecture:** A categorization script assigns each of ~7,364 tariff codes to one of ~15 categories by scanning descriptions for keywords. The result is a static `tariff-hierarchy.json`. A new `TariffCodeBrowser` component (same UX as ICDCodeBrowser) renders the tree. Two new API endpoints serve the hierarchy and category codes.

**Tech Stack:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, existing `/api/search/tariff` endpoint.

**Design doc:** `docs/plans/2026-04-05-tariff-browser-design.md`

---

### Task 1: Create tariff categorization script and generate hierarchy JSON

**Files:**
- Create: `ICDGuard/scripts/generate-tariff-hierarchy.mjs`
- Create: `ICDGuard/public/data/tariff-hierarchy.json` (generated output)

**Step 1: Create the categorization script**

```js
import { readFileSync, writeFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');

const codes = JSON.parse(readFileSync(resolve(root, 'public/data/tariff-codes.json'), 'utf-8'));

// Categories with keyword matchers (order matters — first match wins)
// Each entry: { name, test: (code, desc) => boolean }
const categories = [
  {
    name: 'General Rules & Modifiers',
    test: (code) => parseInt(code) >= 1 && parseInt(code) <= 9,
  },
  {
    name: 'Anaesthesia',
    test: (_code, desc) => /\banaesth/i.test(desc),
  },
  {
    name: 'Radiology & Imaging',
    test: (_code, desc) => /\b(x-ray|radiograph|fluoroscop|mammogra|angiogra|CT scan|MRI\b|magnetic resonance|nuclear medicine|bone densitom|imaging|radiolog)/i.test(desc),
  },
  {
    name: 'Pathology & Laboratory',
    test: (_code, desc) => /\b(culture|assay|antigen|antibod|haemoglobin|glucose|protein determin|cholesterol|enzyme|histol|cytol|PCR|serology|haematol|chromatograph|immunoglobulin|electrophoresis|blood gas|blood count|platelet|coagulat|prothrombin|thrombin|fibrinogen|ferritin|transferrin|bilirubin|creatinin|urea\b|uric acid|potassium|sodium determin|calcium determin|phosphate|magnesium|iron stud|zinc|copper determ|hormone|cortisol|insulin|thyroid|oestriol|oestrogen|progesterone|testosterone|aldosterone|renin|catecholamine|vanillyl|serotonin|tryptoph|indican|phenol|porphyr|aminoacid|galactose|mucopolysacchar|sweat test|drug screen|toxicol|alcohol determ|lithium|digoxin|theophylline|phenytoin|carbamazepine|valproic|gentamicin|vancomycin|cyclosporin|methotrexate|tumour marker|CEA\b|PSA\b|AFP\b|CA\s*1[29]|fungal|bacteri|viral load|genotyp|sequenc|microb|smear|stain|sensitivity|minimum inhibitory)/i.test(desc),
  },
  {
    name: 'Audiology & Speech',
    test: (_code, desc) => /\b(audiolog|audiogram|hearing|cochlear|tympan|vestibul|speech therap|language therap|auditory brainstem|evoked potential|electro-cochleograph|otoacoustic)/i.test(desc),
  },
  {
    name: 'Ophthalmology & Optometry',
    test: (_code, desc) => /\b(ophthalm|optomet|retina|cataract|glaucoma|cornea|vitrect|lensectom|spectacle|visual field|visual acuity|intraocular|keratoplast|enucleation|exenteration|orbital|lacrimal|eyelid|conjunctiv|sclera|trabeculect|iridectom|fundoscop|slit.?lamp|tonometr|contact lens|low vision|neuro.?optomet|binocular instab)/i.test(desc),
  },
  {
    name: 'Obstetrics & Gynaecology',
    test: (_code, desc) => /\b(obstet|gynae|pregnan|foet|fetal|caesarean|hysterect|cervix|cervical dilat|uterus|uterin|vaginal|vulva|labia|episiotom|curettage|colposcop|introitus|amniocentesis|chorionic|ectopic|placent|puerper|mastectom|breast\b)/i.test(desc),
  },
  {
    name: 'Urology',
    test: (_code, desc) => /\b(urolog|ureth|bladder|cystect|cystoscop|prostat|renal|kidney|nephre|nephr|dialysis|lithotri|ureter|hydrocele|varicocele|orchid|orchie|epididym|circumcision|vasectom|penile|scrotal)/i.test(desc),
  },
  {
    name: 'Neurosurgery',
    test: (_code, desc) => /\b(neurosurg|craniotom|laminectom|spinal cord|intracranial|cerebr|meningioma|hydrocephalus|shunt.*brain|nerve block|epidural.*pain|spinal.*inject|discectom)/i.test(desc),
  },
  {
    name: 'Cardiothoracic',
    test: (_code, desc) => /\b(cardio|cardiac|coronary|bypass|heart valve|pacemaker|defibrill|thoracot|thoracoscop|lung\b|pleur|mediast|pneumonect|lobectom|ECMO|aortic|mitral|tricuspid|pulmonary arter|vascular graft|endarterect|embolect|aneurysm)/i.test(desc),
  },
  {
    name: 'Orthopaedics & Fractures',
    test: (_code, desc) => /\b(fracture|arthro|ortho|bone graft|bone\b.*fixat|joint\b|tendon|ligament|amputation|osteotom|osteomyelit|spine|vertebr|scoliosis|meniscect|carpal|tarsal|femor|tibia|fibula|humer|radius.*ulna|patella|pelvi|acetabul|hip replac|knee replac|shoulder replac)/i.test(desc),
  },
  {
    name: 'Surgical Procedures',
    test: (_code, desc) => /\b(excision|incision|repair\b|resection|ligation|sutur|drainage|debridement|exploration|biopsy|graft|transplant|reconstruct|flap\b|stoma|laparoscop|endoscop|hernia|appendic|cholecyst|gastrect|colect|colostom|ileostom|haemorrhoid|fissure|fistula|abscess|cyst\b|lipoma|lesion.*remov|wound|burn\b|scar revision|skin.*graft|tracheostom)/i.test(desc),
  },
  {
    name: 'Consultations',
    test: (_code, desc) => /\b(consult|visit|assessment|counselling|evaluation|examination\b|screening\b)/i.test(desc),
  },
  {
    name: 'Allied Health',
    test: (_code, desc) => /\b(physio|biokinet|occupational therap|dietetic|nutrition|podiatr|chiropract|homeopath|naturopath|acupunctur|psycholog|social work)/i.test(desc),
  },
  {
    name: 'Materials & Medication',
    test: (_code, desc) => /\b(material|medication|medicine|dispensing|drug\b|prosthetic device|implant cost|appliance|orthosis|orthotic|fitting|spectacle frame|nylon|polish)/i.test(desc),
  },
];

// Categorize each code
const categoryMap = new Map();
categories.forEach((c) => categoryMap.set(c.name, []));
categoryMap.set('Other Procedures', []);

let otherCount = 0;
for (const entry of codes) {
  const desc = entry.description || '';
  let matched = false;
  for (const cat of categories) {
    if (cat.test(entry.code, desc)) {
      categoryMap.get(cat.name).push(entry);
      matched = true;
      break;
    }
  }
  if (!matched) {
    categoryMap.get('Other Procedures').push(entry);
    otherCount++;
  }
}

// Build hierarchy
const GROUP_THRESHOLD = 30;
const result = [];

for (const [name, entries] of categoryMap) {
  if (entries.length === 0) continue;
  entries.sort((a, b) => a.code.localeCompare(b.code));

  const cat = { category: name, codeCount: entries.length };

  if (entries.length < GROUP_THRESHOLD) {
    cat.grouped = false;
    cat.codes = entries.map((e) => ({ code: e.code, description: e.description }));
  } else {
    cat.grouped = true;
    // Group by first 2 digits of code
    const subMap = new Map();
    for (const e of entries) {
      const prefix = e.code.slice(0, 2);
      if (!subMap.has(prefix)) subMap.set(prefix, []);
      subMap.get(prefix).push(e);
    }
    cat.subcategories = Array.from(subMap.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([prefix, subCodes]) => ({
        prefix,
        codeCount: subCodes.length,
        codes: subCodes.map((e) => ({ code: e.code, description: e.description })),
      }));
  }
  result.push(cat);
}

// Report
console.log(`Total codes: ${codes.length}`);
console.log(`Categorized: ${codes.length - otherCount}`);
console.log(`Other (uncategorized): ${otherCount}`);
console.log('');
for (const cat of result) {
  console.log(`${cat.category}: ${cat.codeCount} codes${cat.grouped ? ` (${cat.subcategories.length} groups)` : ''}`);
}

const outPath = resolve(root, 'public/data/tariff-hierarchy.json');
writeFileSync(outPath, JSON.stringify(result, null, 2));
console.log(`\nWritten to ${outPath}`);
```

**Step 2: Run the script and check results**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && node scripts/generate-tariff-hierarchy.mjs`

Expected: Script prints category counts. Check that "Other Procedures" is a reasonable size (ideally <20% of total). If too many codes are uncategorized, add more keywords and re-run.

**Step 3: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add scripts/generate-tariff-hierarchy.mjs public/data/tariff-hierarchy.json && git commit -m "feat: add tariff categorization script and hierarchy data"
```

---

### Task 2: Create tariff hierarchy API endpoints

**Files:**
- Create: `ICDGuard/lib/tariff-hierarchy-data.ts`
- Create: `ICDGuard/app/api/tariff/hierarchy/route.ts`
- Create: `ICDGuard/app/api/tariff/category/route.ts`

**Step 1: Create data loader**

`lib/tariff-hierarchy-data.ts`:

```ts
import fs from 'fs';
import path from 'path';

export interface TariffCode {
  code: string;
  description: string;
}

export interface TariffSubcategory {
  prefix: string;
  codeCount: number;
  codes: TariffCode[];
}

export interface TariffCategory {
  category: string;
  codeCount: number;
  grouped: boolean;
  codes?: TariffCode[];
  subcategories?: TariffSubcategory[];
}

let _cache: TariffCategory[] | null = null;

export function getTariffHierarchy(): TariffCategory[] {
  if (_cache) return _cache;

  const filePath = path.join(process.cwd(), 'public', 'data', 'tariff-hierarchy.json');
  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    _cache = JSON.parse(raw) as TariffCategory[];
  } catch {
    console.warn('[ICDGuard] Could not load tariff-hierarchy.json. Run: node scripts/generate-tariff-hierarchy.mjs');
    _cache = [];
  }

  return _cache;
}
```

**Step 2: Create hierarchy endpoint**

`app/api/tariff/hierarchy/route.ts`:

```ts
import { NextResponse } from 'next/server';
import { getTariffHierarchy } from '@/lib/tariff-hierarchy-data';

export async function GET() {
  const hierarchy = getTariffHierarchy();
  // Return just category names and counts (not full code lists)
  const summary = hierarchy.map((cat) => ({
    category: cat.category,
    codeCount: cat.codeCount,
    grouped: cat.grouped,
    subcategoryCount: cat.subcategories?.length ?? 0,
  }));
  return NextResponse.json(summary);
}
```

**Step 3: Create category endpoint**

`app/api/tariff/category/route.ts`:

```ts
import { NextRequest, NextResponse } from 'next/server';
import { getTariffHierarchy } from '@/lib/tariff-hierarchy-data';

export async function GET(req: NextRequest) {
  const name = req.nextUrl.searchParams.get('name') ?? '';
  if (!name) {
    return NextResponse.json({ error: 'Missing name parameter' }, { status: 400 });
  }

  const hierarchy = getTariffHierarchy();
  const cat = hierarchy.find((c) => c.category === name);
  if (!cat) {
    return NextResponse.json({ error: 'Category not found' }, { status: 404 });
  }

  return NextResponse.json(cat);
}
```

**Step 4: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 5: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add lib/tariff-hierarchy-data.ts app/api/tariff/hierarchy/route.ts app/api/tariff/category/route.ts && git commit -m "feat: add tariff hierarchy API endpoints"
```

---

### Task 3: Create TariffCodeBrowser component

**Files:**
- Create: `ICDGuard/components/TariffCodeBrowser.tsx`

**Step 1: Create the component**

Follow the same UX pattern as `ICDCodeBrowser` (read it at `components/ICDCodeBrowser.tsx` for reference). Key differences:

- Fetches `/api/tariff/hierarchy` on mount (returns category summary: name + count)
- Top-level tree items are categories (not chapters)
- Clicking a category fetches `/api/tariff/category?name=X` to get codes
- If `grouped: true`, shows subcategories (by 2-digit prefix) then codes
- If `grouped: false`, shows flat code list
- Search uses `/api/search/tariff` (existing endpoint)
- `navigateToCode` finds which category contains a code by checking the full hierarchy data
- Modal header: "Tariff Code Browser"
- Position memory: same module-level pattern

Props:
```ts
interface TariffCodeBrowserProps {
  mode: 'modal' | 'standalone';
  onSelect: (code: string, description: string) => void;
  fieldId?: string;
  onClose?: () => void;
}
```

**Important implementation notes:**

The hierarchy endpoint returns a summary (no codes). When user clicks a category, fetch the full category data from `/api/tariff/category?name=X`. This avoids loading all 7,364 codes on mount.

For `navigateToCode` in search mode: since we only have the summary on mount, fetch the category data to expand to the right place. The simplest approach: iterate the summary categories and for each, fetch `/api/tariff/category?name=X`, check if the code exists in it. To avoid N fetches, an alternative: the hierarchy JSON already has all codes embedded — load it client-side in a ref on first navigate request.

**Simpler approach for navigateToCode:** On mount, also fetch the full hierarchy (with codes) into a ref but don't render from it — only use it for lookups. This is ~780KB but cached in memory. Or, just skip "Show in tree" for tariff for now and add it later.

Recommended: include "Show in tree" — fetch full hierarchy into a ref on first `navigateToCode` call, cache it.

**Step 2: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 3: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add components/TariffCodeBrowser.tsx && git commit -m "feat: add TariffCodeBrowser component"
```

---

### Task 4: Replace tariff CodeSearchModal in ClaimGroupCard and ClaimCard

**Files:**
- Modify: `ICDGuard/components/ClaimGroupCard.tsx`
- Modify: `ICDGuard/components/ClaimCard.tsx`

**Step 1: Update ClaimGroupCard**

Add import:
```tsx
import TariffCodeBrowser from './TariffCodeBrowser';
```

Find the tariff search block (around line 375-384):
```tsx
{searchField === 'tariff' && (
  <CodeSearchModal
    type="tariff"
    currentValue={tariffValue}
    onSelect={(code, description) => {
      handleApplyCode('tariffCode', code, description);
    }}
    onClose={() => setSearchField(null)}
  />
)}
```

Replace with:
```tsx
{searchField === 'tariff' && (
  <TariffCodeBrowser
    mode="modal"
    fieldId={`${claim.id}-tariff`}
    onSelect={(code, description) => {
      handleApplyCode('tariffCode', code, description);
    }}
    onClose={() => setSearchField(null)}
  />
)}
```

**Step 2: Update ClaimCard**

Add import:
```tsx
import TariffCodeBrowser from './TariffCodeBrowser';
```

Find the tariff search block (around line 191-199) and make the same replacement.

**Step 3: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 4: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add components/ClaimGroupCard.tsx components/ClaimCard.tsx && git commit -m "feat: use TariffCodeBrowser for tariff search in claim cards"
```

---

### Task 5: Add Tariff Codes tab to /search page

**Files:**
- Modify: `ICDGuard/app/search/page.tsx`

**Step 1: Add tariff tab and TariffCodeBrowser**

Read the current file. It has a `CodeTab` type of `'all' | 'ecc'` and two tabs. Update to:

1. Change the type: `type CodeTab = 'all' | 'ecc' | 'tariff';`
2. Add third tab to the `tabs` array: `{ key: 'tariff', label: 'Tariff Codes' }`
3. Add import: `import TariffCodeBrowser from '@/components/TariffCodeBrowser';`
4. Change the browser rendering to conditionally pick the right component:

```tsx
{activeTab === 'tariff' ? (
  <TariffCodeBrowser
    key="tariff"
    mode="standalone"
    onSelect={handleSelect}
  />
) : (
  <ICDCodeBrowser
    key={activeTab}
    mode="standalone"
    codeFilter={activeTab}
    onSelect={handleSelect}
  />
)}
```

**Step 2: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 3: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add app/search/page.tsx && git commit -m "feat: add Tariff Codes tab to /search page"
```

---

### Task 6: Smoke test

**No files changed — verification only.**

**Step 1:** Dev server should be running at `http://localhost:3000`

**Step 2: Test /search page tariff tab**
- Click "Tariff Codes" tab → categories listed with code counts
- Expand a category → subcategories (if grouped) or flat code list
- Click a code → clipboard copy + toast
- Search "fracture" → tariff search results in split view
- Switch to ICD tab → ICD browser restored
- Switch to ECC tab → ECC browser restored

**Step 3: Test tariff modal in /review**
- Upload a test CSV, go to review
- Click 🔍 on tariff field → "Tariff Code Browser" modal opens
- Browse categories, select a code → inserted, modal closes
- ICD 🔍 → ICD browser (unchanged)
- ECC 🔍 → ECC browser (unchanged)

**Step 4: Check categorization quality**
- Browse "Other Procedures" → check if any obviously miscategorized codes should be in a specific category
- If keywords need refinement, update `scripts/generate-tariff-hierarchy.mjs`, re-run, and recommit

**Step 5:** If any fixes needed, commit them.

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Categorization script + hierarchy JSON | `scripts/generate-tariff-hierarchy.mjs`, `public/data/tariff-hierarchy.json` (create) |
| 2 | API endpoints | `lib/tariff-hierarchy-data.ts`, `app/api/tariff/hierarchy/route.ts`, `app/api/tariff/category/route.ts` (create) |
| 3 | TariffCodeBrowser component | `components/TariffCodeBrowser.tsx` (create) |
| 4 | Modal integration | `components/ClaimGroupCard.tsx`, `components/ClaimCard.tsx` (modify) |
| 5 | /search page tab | `app/search/page.tsx` (modify) |
| 6 | Smoke test | — |
