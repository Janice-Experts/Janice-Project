# ICD Synonym Search — Design

**Date:** 2026-04-05

## Goal

Add a synonym/abbreviation lookup layer to ICD search so common SA medical terms, abbreviations, and colloquial names map to the correct ICD codes.

## Decisions

| Aspect | Decision |
|--------|----------|
| Data | New `public/data/icd-synonyms.json` — ~200-300 entries |
| Generation | Script generates initial synonyms from ICD descriptions, focused on common SA terms |
| Scope | Common abbreviations (TB, HIV, UTI), SA colloquial terms (sugar diabetes, high blood), widely-used shorthand |
| Integration | New search tier in existing `/api/search/icd` between code prefix and description keyword match |
| UI changes | None — works through existing search bars |

## Data Format

```json
[
  { "term": "tb", "codes": ["A15", "A16", "A17", "A18", "A19"] },
  { "term": "hiv", "codes": ["B20", "B21", "B22", "B23", "B24"] },
  { "term": "sugar diabetes", "codes": ["E11"] },
  { "term": "high blood", "codes": ["I10", "I11", "I12", "I13", "I15"] },
  { "term": "heart attack", "codes": ["I21", "I22"] },
  { "term": "uti", "codes": ["N39.0"] }
]
```

## Search Tier Order

1. Code prefix match (existing)
2. **Synonym match** — query matches a synonym term → return all codes starting with mapped prefixes (NEW)
3. Description keyword match (existing)
4. Fuzzy fallback (existing)

Synonym matching: case-insensitive, checks if query equals or contains a synonym term.

## Generation Approach

Script reads ICD descriptions and generates common abbreviations and SA colloquial terms for frequently referenced conditions. Output reviewed and saved as static JSON.

## Out of Scope

- UI changes
- Tariff or ECC search synonyms
- Validation engine changes
- Client-side revalidation changes
