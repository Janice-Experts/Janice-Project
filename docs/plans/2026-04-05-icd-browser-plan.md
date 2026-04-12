# ICD Code Browser — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a hierarchical ICD-10 browser (chapter → block → codes) that works as both a modal during claim corrections and a standalone search page.

**Architecture:** A single `ICDCodeBrowser` component powers both contexts. Browse mode shows a collapsible tree; search mode shows a split view with search results (left) and auto-navigating tree (right). Data layer (hierarchy JSON, API endpoints, generation script) is already built.

**Tech Stack:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, existing `/api/icd/hierarchy` and `/api/icd/block` endpoints, existing `/api/search/icd` endpoint.

**Design doc:** `docs/plans/2026-04-05-icd-browser-design.md`

---

## Pre-existing (already built — do NOT rebuild)

- `public/data/icd10-hierarchy.json` — static hierarchy data
- `scripts/generate-hierarchy.mjs` — generates hierarchy from icd10-mit.json
- `lib/icd-hierarchy-data.ts` — server-side loader with caching
- `app/api/icd/hierarchy/route.ts` — GET endpoint returning full hierarchy
- `app/api/icd/block/route.ts` — GET endpoint returning codes for a block (flat or grouped)
- `app/api/search/icd/route.ts` — existing 3-tier ICD search (unchanged)

---

### Task 1: Create ICDCodeBrowser component — browse mode and search mode

**Files:**
- Create: `ICDGuard/components/ICDCodeBrowser.tsx`

**Step 1: Create the component file**

The component fetches hierarchy on mount and renders a collapsible tree: chapters → blocks → codes. When the search bar has text, it switches to split view with search results (left) and tree (right).

```tsx
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Block {
  range: string;
  title: string;
  codeCount: number;
}

interface Chapter {
  chapter: string;
  title: string;
  range: string;
  codeCount: number;
  blocks: Block[];
}

interface CodeEntry {
  code: string;
  description: string;
}

interface Category {
  category: string;
  title: string;
  codes: CodeEntry[];
}

interface BlockResponse {
  block: string;
  title: string;
  grouped: boolean;
  codes?: CodeEntry[];
  categories?: Category[];
}

interface SearchResult {
  code: string;
  description: string;
  score: number;
}

export interface ICDCodeBrowserProps {
  mode: 'modal' | 'standalone';
  onSelect: (code: string, description: string) => void;
  fieldId?: string;
  onClose?: () => void;
}

// ─── Position memory (module-level, survives re-renders but not page reload) ─

let _lastFieldId: string | null = null;
let _lastExpandedChapters: Set<string> = new Set();
let _lastExpandedBlock: string | null = null;

// ─── Component ───────────────────────────────────────────────────────────────

export default function ICDCodeBrowser({ mode, onSelect, fieldId, onClose }: ICDCodeBrowserProps) {
  const [hierarchy, setHierarchy] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);

  // Browse state
  const [expandedChapters, setExpandedChapters] = useState<Set<string>>(new Set());
  const [expandedBlock, setExpandedBlock] = useState<string | null>(null);
  const [blockData, setBlockData] = useState<BlockResponse | null>(null);
  const [blockLoading, setBlockLoading] = useState(false);

  // Search state
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [tooMany, setTooMany] = useState<number | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch hierarchy on mount
  useEffect(() => {
    fetch('/api/icd/hierarchy')
      .then((r) => r.json())
      .then((data: Chapter[]) => {
        setHierarchy(data);
        // Restore position memory if same field
        if (mode === 'modal' && fieldId && fieldId === _lastFieldId) {
          setExpandedChapters(new Set(_lastExpandedChapters));
          if (_lastExpandedBlock) loadBlock(_lastExpandedBlock);
        }
      })
      .finally(() => setLoading(false));
    searchRef.current?.focus();
  }, []);

  // Save position memory on unmount
  useEffect(() => {
    return () => {
      if (mode === 'modal' && fieldId) {
        _lastFieldId = fieldId;
        _lastExpandedChapters = new Set(expandedChapters);
        _lastExpandedBlock = expandedBlock;
      }
    };
  });

  // ─── Browse handlers ─────────────────────────────────────────────────────

  function toggleChapter(chapterId: string) {
    setExpandedChapters((prev) => {
      const next = new Set(prev);
      if (next.has(chapterId)) next.delete(chapterId);
      else next.add(chapterId);
      return next;
    });
  }

  async function loadBlock(range: string) {
    setExpandedBlock(range);
    setBlockLoading(true);
    try {
      const res = await fetch(`/api/icd/block?range=${encodeURIComponent(range)}`);
      const json: BlockResponse = await res.json();
      setBlockData(json);
    } finally {
      setBlockLoading(false);
    }
  }

  function handleBlockClick(range: string) {
    if (expandedBlock === range) {
      setExpandedBlock(null);
      setBlockData(null);
      return;
    }
    loadBlock(range);
  }

  function selectCode(code: string, description: string) {
    onSelect(code, description);
    if (mode === 'modal') onClose?.();
  }

  // ─── Search handlers ─────────────────────────────────────────────────────

  function handleSearchInput(val: string) {
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (val.length < 2) {
      setSearchResults([]);
      setTooMany(null);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const res = await fetch(`/api/search/icd?q=${encodeURIComponent(val)}`);
        const data = await res.json();
        setTooMany(data.tooMany ? data.count : null);
        setSearchResults(data.results ?? []);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
  }

  function navigateToCode(code: string) {
    const letter = code[0];
    const num = parseInt(code.slice(1, 3), 10);

    for (const ch of hierarchy) {
      for (const block of ch.blocks) {
        const [start, end] = block.range.split('-');
        const sL = start[0], sN = parseInt(start.slice(1), 10);
        const eL = end[0], eN = parseInt(end.slice(1), 10);
        let inRange = false;
        if (sL === eL) {
          inRange = letter === sL && num >= sN && num <= eN;
        } else {
          if (letter > sL && letter < eL) inRange = true;
          if (letter === sL && num >= sN) inRange = true;
          if (letter === eL && num <= eN) inRange = true;
        }
        if (inRange) {
          setExpandedChapters((prev) => new Set(prev).add(ch.chapter));
          loadBlock(block.range);
          return;
        }
      }
    }
  }

  // ─── Searching? ───────────────────────────────────────────────────────────

  const isSearching = query.length >= 2;

  // ─── Render helpers ───────────────────────────────────────────────────────

  const maxH = mode === 'modal' ? '60vh' : 'calc(100vh - 220px)';

  const searchBar = (
    <div className="px-4 py-3 border-b border-gray-100">
      <input
        ref={searchRef}
        type="text"
        value={query}
        onChange={(e) => handleSearchInput(e.target.value)}
        placeholder="Search by code or description, or browse below..."
        autoComplete="off"
        spellCheck={false}
        className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-[#1a3a6b]"
      />
    </div>
  );

  const browseTree = (
    <div className="overflow-y-auto" style={{ maxHeight: maxH }}>
      {loading && <p className="text-center text-sm text-gray-400 py-6">Loading hierarchy...</p>}
      {!loading && hierarchy.map((ch) => (
        <div key={ch.chapter}>
          <button
            onClick={() => toggleChapter(ch.chapter)}
            className="w-full text-left px-5 py-3 hover:bg-blue-50 border-b border-gray-50 flex items-center gap-3"
          >
            <span className={`text-xs transition-transform ${expandedChapters.has(ch.chapter) ? 'rotate-90' : ''}`}>▶</span>
            <span className="text-sm font-semibold text-[#1a3a6b]">{ch.range}</span>
            <span className="text-sm text-gray-700 flex-1">{ch.title}</span>
            <span className="text-xs text-gray-400">{ch.codeCount.toLocaleString()} codes</span>
          </button>

          {expandedChapters.has(ch.chapter) && ch.blocks.map((block) => (
            <div key={block.range}>
              <button
                onClick={() => handleBlockClick(block.range)}
                className="w-full text-left pl-10 pr-5 py-2.5 hover:bg-blue-50 border-b border-gray-50 flex items-center gap-3"
              >
                <span className={`text-xs transition-transform ${expandedBlock === block.range ? 'rotate-90' : ''}`}>▶</span>
                <span className="text-xs font-mono font-semibold text-blue-700">{block.range}</span>
                <span className="text-sm text-gray-600 flex-1">{block.title}</span>
                <span className="text-xs text-gray-400">{block.codeCount}</span>
              </button>

              {expandedBlock === block.range && (
                <div className="bg-gray-50 border-b border-gray-100">
                  {blockLoading && <p className="text-center text-xs text-gray-400 py-4">Loading codes...</p>}
                  {!blockLoading && blockData && !blockData.grouped && blockData.codes?.map((c) => (
                    <button
                      key={c.code}
                      onClick={() => selectCode(c.code, c.description)}
                      className="w-full text-left pl-16 pr-5 py-2 hover:bg-blue-100 border-b border-gray-100/50 flex items-baseline gap-2"
                    >
                      <span className="font-mono text-sm font-semibold text-blue-700 shrink-0">{c.code}</span>
                      <span className="text-sm text-gray-600">{c.description}</span>
                    </button>
                  ))}
                  {!blockLoading && blockData && blockData.grouped && blockData.categories?.map((cat) => (
                    <div key={cat.category}>
                      <div className="pl-16 pr-5 py-2 bg-gray-100/80 border-b border-gray-200/50">
                        <span className="font-mono text-xs font-bold text-gray-500">{cat.category}</span>
                        <span className="ml-2 text-xs text-gray-500">{cat.title}</span>
                      </div>
                      {cat.codes.map((c) => (
                        <button
                          key={c.code}
                          onClick={() => selectCode(c.code, c.description)}
                          className="w-full text-left pl-20 pr-5 py-2 hover:bg-blue-100 border-b border-gray-100/50 flex items-baseline gap-2"
                        >
                          <span className="font-mono text-sm font-semibold text-blue-700 shrink-0">{c.code}</span>
                          <span className="text-sm text-gray-600">{c.description}</span>
                        </button>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );

  const searchPanel = (
    <div className="overflow-y-auto border-r border-gray-100" style={{ maxHeight: maxH }}>
      {tooMany && (
        <div className="px-4 py-2 bg-amber-50 border-b border-amber-100">
          <p className="text-xs text-amber-700">Showing 50 of {tooMany.toLocaleString()} results</p>
        </div>
      )}
      {searchLoading && <p className="text-center text-sm text-gray-400 py-6">Searching...</p>}
      {!searchLoading && searchResults.length === 0 && query.length >= 2 && (
        <p className="text-center text-sm text-gray-400 py-6">No results found</p>
      )}
      {!searchLoading && searchResults.map((r) => (
        <div
          key={r.code}
          className="w-full text-left px-4 py-2.5 hover:bg-blue-50 border-b border-gray-50"
        >
          <button
            onClick={() => selectCode(r.code, r.description)}
            className="w-full text-left flex items-baseline gap-2"
          >
            <span className="font-mono text-sm font-semibold text-blue-700">{r.code}</span>
            <span className="text-sm text-gray-600">{r.description}</span>
          </button>
          <button
            onClick={() => navigateToCode(r.code)}
            className="text-xs text-gray-400 hover:text-[#1a3a6b] mt-0.5"
          >
            Show in tree →
          </button>
        </div>
      ))}
    </div>
  );

  // ─── Modal wrapper ────────────────────────────────────────────────────────

  if (mode === 'modal') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
        <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl mx-4 overflow-hidden" onClick={(e) => e.stopPropagation()}>
          <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-600 uppercase tracking-wide">ICD-10 Code Browser</span>
            <button onClick={onClose} className="ml-auto text-gray-400 hover:text-gray-700 text-lg leading-none">✕</button>
          </div>
          {searchBar}
          {isSearching ? (
            <div className="grid grid-cols-2">
              {searchPanel}
              {browseTree}
            </div>
          ) : (
            browseTree
          )}
        </div>
      </div>
    );
  }

  // ─── Standalone ───────────────────────────────────────────────────────────

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
      {searchBar}
      {isSearching ? (
        <div className="grid grid-cols-2">
          {searchPanel}
          {browseTree}
        </div>
      ) : (
        browseTree
      )}
    </div>
  );
}
```

**Step 2: Verify it compiles**

Run: `cd ICDGuard && npx next build 2>&1 | head -30`
Expected: Build succeeds (component not yet imported anywhere).

**Step 3: Commit**

```bash
git add components/ICDCodeBrowser.tsx
git commit -m "feat: add ICDCodeBrowser component with browse and search modes"
```

---

### Task 2: Integrate ICDCodeBrowser as modal in ClaimGroupCard

**Files:**
- Modify: `ICDGuard/components/ClaimGroupCard.tsx`

The ICD 🔍 button currently opens `CodeSearchModal` with `type="icd"`. Change it to open `ICDCodeBrowser` in modal mode instead. Tariff and ECC buttons remain unchanged.

**Step 1: Add import**

At the top of `ClaimGroupCard.tsx`, alongside the existing `CodeSearchModal` import, add:
```tsx
import ICDCodeBrowser from './ICDCodeBrowser';
```

**Step 2: Replace ICD search modal rendering**

In the `LineItem` component, find the block at lines 364-374:

```tsx
{searchField && (
  <CodeSearchModal
    type={searchField}
    currentValue={searchField === 'icd' ? icdValue : tariffValue}
    onSelect={(code, description) => {
      const field = searchField === 'icd' ? 'icdCode' : 'tariffCode';
      handleApplyCode(field, code, description);
    }}
    onClose={() => setSearchField(null)}
  />
)}
```

Replace with:

```tsx
{searchField === 'icd' && (
  <ICDCodeBrowser
    mode="modal"
    fieldId={`${claim.id}-icd`}
    onSelect={(code, description) => {
      handleApplyCode('icdCode', code, description);
    }}
    onClose={() => setSearchField(null)}
  />
)}
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

**Step 3: Verify it compiles**

Run: `cd ICDGuard && npx next build 2>&1 | head -30`

**Step 4: Commit**

```bash
git add components/ClaimGroupCard.tsx
git commit -m "feat: use ICDCodeBrowser modal for ICD search in ClaimGroupCard"
```

---

### Task 3: Integrate ICDCodeBrowser as modal in ClaimCard

**Files:**
- Modify: `ICDGuard/components/ClaimCard.tsx`

Same pattern as Task 2. Read ClaimCard.tsx carefully — variable names differ slightly.

**Step 1: Add import**

```tsx
import ICDCodeBrowser from './ICDCodeBrowser';
```

**Step 2: Replace ICD search modal rendering**

Find the `CodeSearchModal` rendering block (near end of the main component). Apply the same split: `searchField === 'icd'` renders `ICDCodeBrowser`, `searchField === 'tariff'` renders `CodeSearchModal`.

Match the exact variable names and callback patterns used in ClaimCard (read the file first to confirm).

**Step 3: Verify it compiles**

Run: `cd ICDGuard && npx next build 2>&1 | head -30`

**Step 4: Commit**

```bash
git add components/ClaimCard.tsx
git commit -m "feat: use ICDCodeBrowser modal for ICD search in ClaimCard"
```

---

### Task 4: Replace /search page with standalone ICDCodeBrowser

**Files:**
- Modify: `ICDGuard/app/search/page.tsx`

**Step 1: Rewrite the search page**

Replace `app/search/page.tsx` contents with:

```tsx
'use client';

import { useState } from 'react';
import BannerHeader from '@/components/BannerHeader';
import ICDCodeBrowser from '@/components/ICDCodeBrowser';

export default function SearchPage() {
  const [toast, setToast] = useState<string | null>(null);

  function handleSelect(code: string, description: string) {
    navigator.clipboard.writeText(code);
    setToast(`Copied ${code}`);
    setTimeout(() => setToast(null), 1500);
  }

  return (
    <div className="bg-slate-50 min-h-screen">
      <BannerHeader />

      <main className="max-w-5xl mx-auto px-4 py-8">
        <ICDCodeBrowser
          mode="standalone"
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

**Step 2: Verify it compiles**

Run: `cd ICDGuard && npx next build 2>&1 | head -30`

**Step 3: Commit**

```bash
git add app/search/page.tsx
git commit -m "feat: replace /search page with standalone ICDCodeBrowser"
```

---

### Task 5: Manual smoke test

**No files changed — verification only.**

**Step 1:** Start dev server: `cd ICDGuard && npm run dev`

**Step 2: Test browse mode on /search**
- All 22 chapters render with code counts
- Click chapter I → blocks expand
- Click block A00-A09 → flat code list (<15 codes)
- Click a code → clipboard copy + toast
- Click a large block (e.g. I20-I25) → grouped by 3-digit category

**Step 3: Test search mode on /search**
- Type "diabetes" → split view appears
- "Show in tree →" navigates tree
- Click search result → copies code
- Clear search → back to browse

**Step 4: Test modal in /review**
- Upload test CSV, go to review
- 🔍 on ICD field → ICDCodeBrowser modal (max-w-4xl)
- Select code → inserted into field, modal closes
- 🔍 on tariff field → old CodeSearchModal (max-w-2xl)
- 🔍 on ECC field → old CodeSearchModal

**Step 5: Test position memory**
- Open ICD browser, expand chapter + block
- Close and reopen same field → state restored
- Open different field → starts fresh

**Step 6:** If any fixes needed, commit them.

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | ICDCodeBrowser component | `components/ICDCodeBrowser.tsx` (create) |
| 2 | Modal integration — ClaimGroupCard | `components/ClaimGroupCard.tsx` (modify) |
| 3 | Modal integration — ClaimCard | `components/ClaimCard.tsx` (modify) |
| 4 | Standalone /search page | `app/search/page.tsx` (modify) |
| 5 | Manual smoke test | — |
