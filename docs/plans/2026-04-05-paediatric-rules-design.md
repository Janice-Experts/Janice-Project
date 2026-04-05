# Paediatric ICD Rules Expansion — Design

**Date:** 2026-04-05

## Goal

Expand age-based ICD validation to catch adult codes on children and paediatric codes on adults, using four age bands. All new rules are warnings unless 100% certain errors.

## Age Bands

| Band | Threshold | Severity |
|------|-----------|----------|
| Neonate | >28 days with P-codes | Error (already done) |
| Infant | >1 year with Z38 liveborn codes | Error (100% wrong) |
| Child | <12 years with adult degenerative codes | Warning |
| Adolescent | <18 years with adult-only codes | Warning |
| Adult | ≥18 years with paediatric-only codes | Warning (expand existing) |

## Area 1: Adult codes flagged on children

### Under 12 — warning

| Prefix | Condition | Code count |
|--------|-----------|------------|
| M15-M19 | Osteoarthritis | ~80 |
| M80-M81 | Osteoporosis | ~405 |
| I70 | Atherosclerosis | ~10 |
| E11 | Type 2 diabetes | ~10 |

### Under 18 — warning

| Prefix | Condition | Code count |
|--------|-----------|------------|
| G20 | Parkinson's | 1 |
| G30 | Alzheimer's | 4 |
| F00-F03 | Dementia | ~15 |
| R54 | Senility | 1 |
| N95 | Menopausal disorders | 6 |
| N40 | Prostatic hyperplasia | 1 |
| N41 | Prostatitis | 6 |
| C61 | Prostate cancer | 1 |

## Area 3: Tighter age bands

- Z38 (liveborn infant, 9 codes): Error if >1 year old — only valid at birth
- P-codes: Unchanged (error if >28 days)

## Area 4: Paediatric codes on adults (≥18 — warning)

Expand existing 5-code list to also include:
- Z38.0-Z38.9 (liveborn infant)

Keep conservative — only codes clearly paediatric-only.

## Implementation

- Modify: `lib/validators/demographics.ts` — add lookup arrays and rules
- Modify: `lib/client-revalidate.ts` — mirror new rules for client-side re-validation

## Out of Scope

- Tariff-age validation (deferred)
- UI changes
- API changes
