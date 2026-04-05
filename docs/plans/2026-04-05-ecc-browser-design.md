# ECC Browser — Design

**Date:** 2026-04-05

## Goal

Add External Cause Code browsing to the existing ICD browser component, both as a modal during claim corrections and on the /search page with tabs.

## Decisions

| Aspect | Decision |
|--------|----------|
| Component | Add `codeFilter: 'all' \| 'ecc'` prop to `ICDCodeBrowser` (default: `'all'`) |
| Hierarchy (ecc mode) | Filter to chapter XX only (V01-Y98) — client-side filter, no new API |
| Search (ecc mode) | Use `/api/search/ecc` instead of `/api/search/icd` |
| Header (ecc modal) | "External Cause Code Browser" |
| ECC modal | ClaimGroupCard + ClaimCard: ECC 🔍 button opens `ICDCodeBrowser` with `codeFilter="ecc"` |
| /search page | Pill tabs above browser: "ICD-10 Codes" (default) and "External Cause Codes" |
| Tab styling | Filled pill tabs matching navy brand colour (#1a3a6b) |

## Component Changes

### ICDCodeBrowser — new prop

```ts
interface ICDCodeBrowserProps {
  mode: 'modal' | 'standalone';
  onSelect: (code: string, description: string) => void;
  fieldId?: string;
  onClose?: () => void;
  codeFilter?: 'all' | 'ecc';  // new — default 'all'
}
```

When `codeFilter === 'ecc'`:
- Filter hierarchy response to only chapter XX (range V01-Y98)
- Search uses `/api/search/ecc` instead of `/api/search/icd`
- Modal header: "External Cause Code Browser"

### /search page — tabs

Pill tabs rendered above the `ICDCodeBrowser` component:
- "ICD-10 Codes" (active by default)
- "External Cause Codes"
- Switching tabs changes the `codeFilter` prop passed to `ICDCodeBrowser`
- Active tab: navy background, white text
- Inactive tab: white background, navy text, border

### Modal integration

ClaimGroupCard and ClaimCard: replace the ECC `CodeSearchModal` with `ICDCodeBrowser` in modal mode with `codeFilter="ecc"`.

## Out of Scope

- New API endpoints
- Tariff browsing
- Validation engine changes
- Hierarchy data changes
