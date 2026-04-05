# Import Format Mapper — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When a CSV doesn't match any known parser, show a column mapping UI so users can map their headers to ICDGuard fields, then validate using that mapping.

**Architecture:** Client-side detection reads CSV headers before upload. If unknown and no saved mapping in localStorage, a `ColumnMapper` component appears. User maps columns, mapping is saved, then the file is sent to the server with a `mapping` JSON field. The server uses the mapping in a new `parseCustom` function instead of the generic guesser.

**Tech Stack:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, localStorage, PapaParse (already installed).

**Design doc:** `docs/plans/2026-04-05-import-mapper-design.md`

---

## Pre-reading

- Upload page: `app/page.tsx` — calls `handleUpload(file, system)`
- Upload component: `components/UploadZone.tsx` — file selection + source system cards
- Parser index: `lib/parsers/index.ts` — `detectSourceSystem()`, `parseFile()`, `parseGeneric()`
- Validate API: `app/api/validate/route.ts` — receives FormData, calls `parseFile()`
- Types: `lib/types.ts` — `ClaimRow` interface

---

### Task 1: Create mapping utilities (localStorage + header hashing)

**Files:**
- Create: `ICDGuard/lib/column-mapping.ts`

**Step 1: Create the mapping utilities file**

```ts
// ICDGuard field keys that a CSV column can be mapped to
export const ICDGUARD_FIELDS = [
  { key: 'patientId', label: 'Patient ID', required: true },
  { key: 'patientName', label: 'Patient Name', required: false },
  { key: 'gender', label: 'Gender', required: false },
  { key: 'dob', label: 'Date of Birth', required: false },
  { key: 'serviceDate', label: 'Service Date', required: true },
  { key: 'icdCode', label: 'ICD Code', required: true },
  { key: 'tariffCode', label: 'Tariff Code', required: true },
  { key: 'quantity', label: 'Quantity', required: false },
  { key: 'amount', label: 'Amount', required: false },
  { key: 'provider', label: 'Provider', required: false },
] as const;

export type IcdGuardField = (typeof ICDGUARD_FIELDS)[number]['key'];

export const REQUIRED_FIELDS: IcdGuardField[] = ICDGUARD_FIELDS
  .filter((f) => f.required)
  .map((f) => f.key);

// A mapping: CSV header → ICDGuard field (or null = skip)
export type ColumnMapping = Record<string, IcdGuardField | null>;

export interface SavedMapping {
  headerHash: string;
  headers: string[];
  mapping: ColumnMapping;
  savedAt: string; // ISO date
}

const STORAGE_KEY = 'icdguard-mappings';

/** Simple hash of sorted headers to identify a format */
export function hashHeaders(headers: string[]): string {
  const sorted = headers.map((h) => h.toLowerCase().trim()).sort().join('|');
  let hash = 0;
  for (let i = 0; i < sorted.length; i++) {
    hash = ((hash << 5) - hash + sorted.charCodeAt(i)) | 0;
  }
  return 'map_' + Math.abs(hash).toString(36);
}

/** Get all saved mappings from localStorage */
export function getSavedMappings(): SavedMapping[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/** Find a saved mapping that matches these headers */
export function findSavedMapping(headers: string[]): SavedMapping | null {
  const hash = hashHeaders(headers);
  return getSavedMappings().find((m) => m.headerHash === hash) ?? null;
}

/** Save a mapping to localStorage */
export function saveMapping(headers: string[], mapping: ColumnMapping): void {
  if (typeof window === 'undefined') return;
  const hash = hashHeaders(headers);
  const saved = getSavedMappings().filter((m) => m.headerHash !== hash);
  saved.push({ headerHash: hash, headers, mapping, savedAt: new Date().toISOString() });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
}

/** Check if all required fields are mapped */
export function getMissingRequiredFields(mapping: ColumnMapping): string[] {
  const mapped = new Set(Object.values(mapping).filter(Boolean));
  return REQUIRED_FIELDS.filter((f) => !mapped.has(f));
}

/** Parse CSV headers from raw text (first line) */
export function extractHeaders(csvText: string): string[] {
  const firstLine = csvText.split(/\r?\n/)[0] ?? '';
  return firstLine.split(',').map((h) => h.trim().replace(/^"|"$/g, ''));
}

/** Extract preview rows (first N data rows) */
export function extractPreviewRows(csvText: string, count: number = 5): string[][] {
  const lines = csvText.split(/\r?\n/).filter(Boolean);
  return lines.slice(1, 1 + count).map((line) => {
    const result: string[] = [];
    let current = '';
    let inQuote = false;
    for (const ch of line) {
      if (ch === '"') { inQuote = !inQuote; }
      else if (ch === ',' && !inQuote) { result.push(current.trim()); current = ''; }
      else { current += ch; }
    }
    result.push(current.trim());
    return result;
  });
}
```

**Step 2: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 3: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add lib/column-mapping.ts && git commit -m "feat: add column mapping utilities for import format mapper"
```

---

### Task 2: Create ColumnMapper component

**Files:**
- Create: `ICDGuard/components/ColumnMapper.tsx`

**Step 1: Create the mapper component**

This component shows:
- A white card with navy header
- A table: each row = one CSV column header. Left cell = header name + preview values. Right cell = dropdown to select ICDGuard field.
- Below the table: list of unmapped required fields (in red)
- "Save & Validate" button (disabled until all required fields mapped)
- "Back" link to return to upload

**CRITICAL STYLING REQUIREMENTS — match ICDGuard design language:**
- Page background: `bg-slate-400` (same as upload page main area)
- Card: `bg-white rounded-xl shadow-sm border border-slate-200 p-8`
- Header text: `text-2xl font-bold text-[#1a3a6b]`
- Subtext: `text-gray-500 text-sm`
- Table header row: `bg-slate-50 text-xs font-semibold text-slate-600 uppercase`
- Table body: alternating `bg-white` / `bg-slate-50` rows
- Table text: `text-sm text-gray-900` for headers, `text-xs text-gray-500` for preview data
- Dropdowns: `border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-[#1a3a6b]`
- Required field warning: `text-red-500 text-sm`
- Disabled button: `bg-gray-300 cursor-not-allowed text-white`
- Active button: `bg-[#1a3a6b] text-white hover:bg-[#15305a]`
- Back link: `text-[#1a3a6b] hover:underline text-sm`

Props:
```ts
interface ColumnMapperProps {
  headers: string[];
  previewRows: string[][];
  onSave: (mapping: ColumnMapping) => void;
  onBack: () => void;
}
```

The component:
1. Initialises mapping state: each header → `null` (unmapped)
2. Auto-suggests mappings based on header name similarity (e.g. "patient_id" → patientId, "icd_code" → icdCode). Use a simple keyword match: if header contains "icd" or "diagnosis" → suggest icdCode, etc. These are just defaults — user can change.
3. Shows the table with dropdowns. Each dropdown has "— Skip —" as default plus all ICDGuard fields. Fields already mapped elsewhere are shown with "(mapped)" and still selectable (selecting moves the mapping).
4. Shows missing required fields below the table.
5. "Save & Validate" enabled only when `getMissingRequiredFields()` returns empty.

Auto-suggest keywords (for initial dropdown values):
```ts
const SUGGEST_MAP: Record<string, string[]> = {
  patientId: ['patient_id', 'pat_id', 'member_no', 'member_id', 'patient id', 'account'],
  patientName: ['patient_name', 'pat_name', 'member_name', 'name'],
  gender: ['gender', 'sex'],
  dob: ['dob', 'date_of_birth', 'birth_date', 'birth'],
  serviceDate: ['service_date', 'date_of_service', 'date', 'visit_date'],
  icdCode: ['icd_code', 'icd', 'icd10', 'diagnosis', 'icd_10'],
  tariffCode: ['tariff_code', 'tariff', 'procedure_code', 'procedure', 'proc_code'],
  quantity: ['quantity', 'qty', 'units'],
  amount: ['amount', 'total', 'charged', 'fee'],
  provider: ['provider', 'doctor', 'doctor_name', 'provider_name'],
};
```

**Step 2: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 3: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add components/ColumnMapper.tsx && git commit -m "feat: add ColumnMapper component for unknown CSV formats"
```

---

### Task 3: Add custom mapping parser to server

**Files:**
- Modify: `ICDGuard/lib/parsers/index.ts`
- Modify: `ICDGuard/app/api/validate/route.ts`

**Step 1: Add `parseCustom` function to parsers/index.ts**

Add this function after the existing `parseGeneric` function (around line 107):

```ts
/** Parse CSV using a user-defined column mapping */
export function parseCustom(content: string, mapping: Record<string, string | null>): ClaimRow[] {
  const lines = content.split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) return [];

  const headers = lines[0].split(',').map((h) => h.trim().replace(/"/g, ''));

  // Build reverse map: ICDGuard field → column index
  const fieldToIndex = new Map<string, number>();
  for (const [header, field] of Object.entries(mapping)) {
    if (!field) continue;
    const idx = headers.findIndex((h) => h.toLowerCase().trim().replace(/"/g, '') === header.toLowerCase().trim());
    if (idx !== -1) fieldToIndex.set(field, idx);
  }

  return lines.slice(1).map((line, i) => {
    const cols = splitCsv(line);
    const get = (field: string) => {
      const idx = fieldToIndex.get(field);
      return idx !== undefined ? (cols[idx]?.trim().replace(/"/g, '') ?? '') : '';
    };

    return {
      id: String(i + 1),
      patientId: get('patientId'),
      patientName: get('patientName'),
      gender: normaliseGender(get('gender')),
      dob: get('dob'),
      serviceDate: get('serviceDate'),
      icdCode: get('icdCode'),
      tariffCode: get('tariffCode'),
      treatmentCode: '',
      quantity: Number(get('quantity')) || 1,
      amount: Number(get('amount')) || 0,
      provider: get('provider'),
      raw: Object.fromEntries(headers.map((h, idx) => [h, cols[idx]?.trim().replace(/"/g, '') ?? ''])),
      corrections: {},
    };
  });
}
```

Note: `splitCsv` already exists at the bottom of the file (line 110-120) and `normaliseGender` is imported at the top.

**Step 2: Update validate API to accept mapping**

In `app/api/validate/route.ts`, after reading `system` from formData (line 24), also read the mapping:

```ts
const mappingStr = formData.get('mapping') as string | undefined;
```

Then change the parsing logic (around line 40) to use custom parsing when a mapping is provided:

```ts
let claims, sourceSystem, warnings;
if (mappingStr) {
  const mapping = JSON.parse(mappingStr);
  claims = parseCustom(content, mapping);
  sourceSystem = 'custom' as any;
  warnings = [] as string[];
} else {
  const result = parseFile(content, file.name, system ?? undefined);
  claims = result.claims;
  sourceSystem = result.sourceSystem;
  warnings = result.warnings;
}
```

Also add the import for `parseCustom` at the top:
```ts
import { parseFile, parseCustom } from '@/lib/parsers';
```

And update the `SourceSystem` type in `lib/parsers/index.ts` to include `'custom'`:
```ts
export type SourceSystem = 'goodx' | 'elixir' | 'medinol' | 'healthbridge' | 'custom' | 'unknown';
```

**Step 3: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 4: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add lib/parsers/index.ts app/api/validate/route.ts && git commit -m "feat: add custom mapping parser and API support"
```

---

### Task 4: Integrate mapper into upload flow

**Files:**
- Modify: `ICDGuard/app/page.tsx`
- Modify: `ICDGuard/components/UploadZone.tsx`

**Step 1: Update UploadZone to detect unknown formats client-side**

The UploadZone currently calls `onUpload(file, system)` directly. Change it to also read the file content client-side, check headers against saved mappings, and either:
- Call `onUpload(file, system)` for known formats (existing flow)
- Call a new `onNeedsMapping(file, headers, previewRows)` callback for unknown formats with no saved mapping
- Call `onUpload(file, system, mapping)` for unknown formats with a saved mapping

Update the `UploadZoneProps` interface:

```ts
interface UploadZoneProps {
  onUpload: (file: File, system: string, mapping?: ColumnMapping) => void;
  onNeedsMapping: (file: File, headers: string[], previewRows: string[][]) => void;
  loading: boolean;
}
```

In the submit handler, read the file, detect format, check for saved mapping:

```ts
async function handleSubmit(e: React.FormEvent) {
  e.preventDefault();
  if (!selectedFile) return;

  // If user explicitly chose a system (not auto-detect), use it directly
  if (system) {
    onUpload(selectedFile, system);
    return;
  }

  // Auto-detect: read file content and check headers
  const text = await readFileAsText(selectedFile);
  const headers = extractHeaders(text);
  
  // Check if it matches a known parser by looking at headers
  const firstLine = text.split(/\r?\n/)[0]?.toLowerCase() ?? '';
  const isKnown = firstLine.includes('goodx') || firstLine.includes('elixir') 
    || firstLine.includes('medinol') || firstLine.includes('healthbridge')
    || firstLine.includes('pat_id') || (firstLine.includes('member') && firstLine.includes('diagnosis'))
    || firstLine.includes('patient_no') || firstLine.includes('icd10')
    || (firstLine.includes('account') && firstLine.includes('procedure'));

  if (isKnown) {
    onUpload(selectedFile, '');
    return;
  }

  // Unknown format — check for saved mapping
  const saved = findSavedMapping(headers);
  if (saved) {
    onUpload(selectedFile, '', saved.mapping);
    return;
  }

  // No saved mapping — need manual mapping
  const previewRows = extractPreviewRows(text);
  onNeedsMapping(selectedFile, headers, previewRows);
}
```

Add a helper to read file as text:
```ts
async function readFileAsText(file: File): Promise<string> {
  if (file.name.toLowerCase().endsWith('.xlsx')) {
    const { read, utils } = await import('xlsx');
    const buffer = await file.arrayBuffer();
    const wb = read(buffer, { type: 'array' });
    const ws = wb.Sheets[wb.SheetNames[0]];
    return utils.sheet_to_csv(ws);
  }
  return file.text();
}
```

Add imports at the top:
```ts
import { extractHeaders, extractPreviewRows, findSavedMapping, ColumnMapping } from '@/lib/column-mapping';
```

**Step 2: Update the upload page to show ColumnMapper when needed**

In `app/page.tsx`, add state for the mapper flow and render ColumnMapper when needed:

```tsx
import ColumnMapper from '@/components/ColumnMapper';
import { ColumnMapping, saveMapping } from '@/lib/column-mapping';

// Add state
const [mapperData, setMapperData] = useState<{
  file: File;
  headers: string[];
  previewRows: string[][];
} | null>(null);

// Add handler for needs-mapping
function handleNeedsMapping(file: File, headers: string[], previewRows: string[][]) {
  setMapperData({ file, headers, previewRows });
}

// Add handler for mapper save
function handleMapperSave(mapping: ColumnMapping) {
  if (!mapperData) return;
  saveMapping(mapperData.headers, mapping);
  handleUpload(mapperData.file, '', mapping);
  setMapperData(null);
}

// Update handleUpload to accept optional mapping
async function handleUpload(file: File, system: string, mapping?: ColumnMapping) {
  // ... existing code, but add mapping to FormData:
  if (mapping) formData.append('mapping', JSON.stringify(mapping));
  // ... rest unchanged
}
```

In the JSX, conditionally render the mapper or the upload form:

```tsx
{mapperData ? (
  <ColumnMapper
    headers={mapperData.headers}
    previewRows={mapperData.previewRows}
    onSave={handleMapperSave}
    onBack={() => setMapperData(null)}
  />
) : (
  <>
    <h1 className="text-2xl font-bold text-[#1a3a6b] mb-2">Upload Claim File</h1>
    <p className="text-gray-500 text-sm mb-8">...</p>
    <UploadZone onUpload={handleUpload} onNeedsMapping={handleNeedsMapping} loading={loading} />
    {error && ...}
  </>
)}
```

**Step 3: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 4: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add app/page.tsx components/UploadZone.tsx && git commit -m "feat: integrate column mapper into upload flow"
```

---

### Task 5: Smoke test

**No files changed — verification only.**

**Step 1:** Dev server should be running at `http://localhost:3000`

**Step 2: Test with a known format**
- Upload an Elixir CSV (e.g. `test data/elixir_test.csv`) with Auto-detect
- Should go straight to validation → review page (no mapper shown)

**Step 3: Test with unknown format (mapper should appear)**
- Create a test CSV with unusual column names:

```csv
claim_ref,full_name,visit_dt,dx_code,proc_code,bill_amt,doc,birthdate,m_f
C001,John Smith,2026-04-01,J06.9,0190,850.00,Dr Adams,1985-03-15,M
C002,Jane Doe,2026-04-01,M17.1,0401,1200.00,Dr Brown,2018-06-01,F
C003,Bob Wilson,2026-04-01,Z38.0,0190,500.00,Dr Adams,2024-01-15,M
```

- Upload with Auto-detect → mapper screen should appear
- Verify styling: navy header, white card, dropdowns styled correctly, no white-on-white text
- Map columns: claim_ref → Patient ID, full_name → Patient Name, visit_dt → Service Date, dx_code → ICD Code, proc_code → Tariff Code, bill_amt → Amount, doc → Provider, birthdate → DOB, m_f → Gender
- Check that auto-suggest populates some fields based on header similarity
- Check that "Save & Validate" is disabled until all 4 required fields are mapped
- Click "Save & Validate" → should proceed to validation and show results on review page

**Step 4: Test saved mapping reuse**
- Upload the same unusual CSV again
- Should skip the mapper and go straight to validation (saved mapping auto-applied)

**Step 5: Test missing required fields**
- Create a CSV with no ICD-like column at all:

```csv
name,date,amount
John,2026-04-01,500
```

- Upload → mapper appears
- Try to map: only Patient Name, Service Date, Amount available
- "Save & Validate" should stay disabled
- Warning should show: missing ICD Code, Tariff Code, Patient ID

**Step 6:** If any fixes needed, commit them.

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Mapping utilities (types, localStorage, hashing) | `lib/column-mapping.ts` (create) |
| 2 | ColumnMapper component | `components/ColumnMapper.tsx` (create) |
| 3 | Custom parser + API support | `lib/parsers/index.ts`, `app/api/validate/route.ts` (modify) |
| 4 | Upload flow integration | `app/page.tsx`, `components/UploadZone.tsx` (modify) |
| 5 | Smoke test | — |
