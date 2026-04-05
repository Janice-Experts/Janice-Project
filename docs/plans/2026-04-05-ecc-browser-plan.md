# ECC Browser — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add External Cause Code browsing by extending ICDCodeBrowser with a `codeFilter` prop, integrating it into the ECC modal and adding tabs to the /search page.

**Architecture:** Add a `codeFilter: 'all' | 'ecc'` prop to ICDCodeBrowser. When `'ecc'`, the component filters hierarchy to chapter XX (V01-Y98) and searches via `/api/search/ecc`. The /search page gets pill tabs to switch between ICD and ECC modes.

**Tech Stack:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4. No new API endpoints or data files needed.

**Design doc:** `docs/plans/2026-04-05-ecc-browser-design.md`

---

### Task 1: Add `codeFilter` prop to ICDCodeBrowser

**Files:**
- Modify: `ICDGuard/components/ICDCodeBrowser.tsx`

**Step 1: Update the props interface and component signature**

In `ICDCodeBrowser.tsx`, change the props interface (line 46-51) from:

```tsx
export interface ICDCodeBrowserProps {
  mode: 'modal' | 'standalone';
  onSelect: (code: string, description: string) => void;
  fieldId?: string;
  onClose?: () => void;
}
```

To:

```tsx
export interface ICDCodeBrowserProps {
  mode: 'modal' | 'standalone';
  onSelect: (code: string, description: string) => void;
  fieldId?: string;
  onClose?: () => void;
  codeFilter?: 'all' | 'ecc';
}
```

Update the component destructuring (line 61) to include `codeFilter = 'all'`:

```tsx
export default function ICDCodeBrowser({ mode, onSelect, fieldId, onClose, codeFilter = 'all' }: ICDCodeBrowserProps) {
```

**Step 2: Filter hierarchy when codeFilter is 'ecc'**

After the hierarchy is fetched and set (inside the `.then()` at line 90), apply a filter. Change the hierarchy fetch `.then()` block to:

```tsx
.then((data: Chapter[]) => {
  const filtered = codeFilter === 'ecc'
    ? data.filter((ch) => ch.range === 'V01-Y98')
    : data;
  setHierarchy(filtered);
  // Restore position memory if same field
  if (mode === 'modal' && fieldId && fieldId === _lastFieldId) {
    setExpandedChapters(new Set(_lastExpandedChapters));
    if (_lastExpandedBlock) loadBlockRef.current?.(_lastExpandedBlock);
  }
})
```

**Step 3: Use correct search endpoint**

Change the search fetch URL (line 166) from hardcoded `/api/search/icd` to dynamic:

```tsx
const searchEndpoint = codeFilter === 'ecc' ? '/api/search/ecc' : '/api/search/icd';
```

Then use it in the fetch call:

```tsx
const res = await fetch(`${searchEndpoint}?q=${encodeURIComponent(val)}`);
```

**Step 4: Update modal header text**

Change the modal header (line 336) from hardcoded "ICD-10 Code Browser" to dynamic:

```tsx
<span className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
  {codeFilter === 'ecc' ? 'External Cause Code Browser' : 'ICD-10 Code Browser'}
</span>
```

**Step 5: Update search placeholder**

Change the search input placeholder (line 220) to be context-aware:

```tsx
placeholder={codeFilter === 'ecc'
  ? "Search external cause codes, or browse below..."
  : "Search by code or description, or browse below..."}
```

**Step 6: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`
Expected: Build succeeds. Existing usage (no `codeFilter` prop) defaults to `'all'` — no breaking change.

**Step 7: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add components/ICDCodeBrowser.tsx && git commit -m "feat: add codeFilter prop to ICDCodeBrowser for ECC support"
```

---

### Task 2: Replace ECC CodeSearchModal with ICDCodeBrowser in ClaimGroupCard

**Files:**
- Modify: `ICDGuard/components/ClaimGroupCard.tsx`

**Step 1: Replace the ECC search modal**

In `ClaimGroupCard.tsx`, find the ECC search block (lines 385-392):

```tsx
{eccSearch && (
  <CodeSearchModal
    type="ecc"
    currentValue={eccValue}
    onSelect={(code, description) => handleApplyEcc(code, description)}
    onClose={() => setEccSearch(false)}
  />
)}
```

Replace with:

```tsx
{eccSearch && (
  <ICDCodeBrowser
    mode="modal"
    codeFilter="ecc"
    fieldId={`${claim.id}-ecc`}
    onSelect={(code, description) => handleApplyEcc(code, description)}
    onClose={() => setEccSearch(false)}
  />
)}
```

`ICDCodeBrowser` is already imported in this file from Task 2 of the ICD browser work.

**Step 2: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 3: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add components/ClaimGroupCard.tsx && git commit -m "feat: use ICDCodeBrowser for ECC search in ClaimGroupCard"
```

---

### Task 3: Replace ECC CodeSearchModal with ICDCodeBrowser in ClaimCard

**Files:**
- Modify: `ICDGuard/components/ClaimCard.tsx`

**Step 1: Replace the ECC search modal**

In `ClaimCard.tsx`, find the ECC search block (lines 201-208):

```tsx
{eccSearch && (
  <CodeSearchModal
    type="ecc"
    currentValue={eccValue}
    onSelect={(code, description) => handleApplyEcc(code, description)}
    onClose={() => setEccSearch(false)}
  />
)}
```

Replace with:

```tsx
{eccSearch && (
  <ICDCodeBrowser
    mode="modal"
    codeFilter="ecc"
    fieldId={`${claim.id}-ecc`}
    onSelect={(code, description) => handleApplyEcc(code, description)}
    onClose={() => setEccSearch(false)}
  />
)}
```

`ICDCodeBrowser` is already imported in this file.

**Step 2: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 3: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add components/ClaimCard.tsx && git commit -m "feat: use ICDCodeBrowser for ECC search in ClaimCard"
```

---

### Task 4: Add tabs to /search page

**Files:**
- Modify: `ICDGuard/app/search/page.tsx`

**Step 1: Add tab state and tab UI**

Replace the contents of `app/search/page.tsx` with:

```tsx
'use client';

import { useState } from 'react';
import BannerHeader from '@/components/BannerHeader';
import ICDCodeBrowser from '@/components/ICDCodeBrowser';

type CodeTab = 'all' | 'ecc';

export default function SearchPage() {
  const [toast, setToast] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<CodeTab>('all');

  function handleSelect(code: string, description: string) {
    navigator.clipboard.writeText(code);
    setToast(`Copied ${code}`);
    setTimeout(() => setToast(null), 1500);
  }

  const tabs: { key: CodeTab; label: string }[] = [
    { key: 'all', label: 'ICD-10 Codes' },
    { key: 'ecc', label: 'External Cause Codes' },
  ];

  return (
    <div className="bg-slate-50 min-h-screen">
      <BannerHeader />

      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex gap-2 mb-4">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'bg-[#1a3a6b] text-white'
                  : 'bg-white text-[#1a3a6b] border border-[#1a3a6b] hover:bg-blue-50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <ICDCodeBrowser
          key={activeTab}
          mode="standalone"
          codeFilter={activeTab}
          onSelect={handleSelect}
        />

        {toast && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-[#1a3a6b] text-white px-4 py-2 rounded-lg shadow-lg text-sm z-50">
            {toast}
          </div>
        )}
      </main>
    </div>
  );
}
```

Note: `key={activeTab}` forces React to remount the component when switching tabs, which resets browse/search state cleanly.

**Step 2: Verify build**

Run: `cd "C:/Projects/Janice Project/ICDGuard" && npx next build 2>&1 | tail -20`

**Step 3: Commit**

```bash
cd "C:/Projects/Janice Project/ICDGuard" && git add app/search/page.tsx && git commit -m "feat: add ICD/ECC tabs to /search page"
```

---

### Task 5: Manual smoke test

**No files changed — verification only.**

**Step 1:** Start dev server: `cd ICDGuard && npm run dev`

**Step 2: Test /search page tabs**
- Default tab "ICD-10 Codes" shows all 22 chapters
- Click "External Cause Codes" tab → shows only chapter XX
- Blocks visible: Transport accidents (V01-V99), Falls (W00-W19), etc.
- Search "fall" in ECC tab → results from V/W/X/Y codes only
- Switch back to ICD tab → full hierarchy restored

**Step 3: Test ECC modal in /review**
- Upload a test CSV, go to review
- Find a claim with an ECC issue (S/T code without external cause)
- Click 🔍 on ECC field → "External Cause Code Browser" modal opens
- Browse chapter XX blocks, select a V/W/X/Y code → inserted into field
- Modal closes, code applied

**Step 4:** If any fixes needed, commit them.

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Add `codeFilter` prop to ICDCodeBrowser | `components/ICDCodeBrowser.tsx` (modify) |
| 2 | ECC modal in ClaimGroupCard | `components/ClaimGroupCard.tsx` (modify) |
| 3 | ECC modal in ClaimCard | `components/ClaimCard.tsx` (modify) |
| 4 | Tabs on /search page | `app/search/page.tsx` (modify) |
| 5 | Smoke test | — |
