# ClaimGuard MVP — Design Document

**Date:** 2026-03-06
**Branch:** feature/claimguard-mvp

---

## Overview

ClaimGuard is a web-based claim validation tool for South African clinics and billing companies.
It reduces claim rejections caused by ICD/CPT coding errors, missing modifiers, and duplicates.

---

## Architecture

- **Backend:** FastAPI (Python 3.10+), pure JSON REST API
- **Frontend:** Vanilla HTML + CSS + JavaScript (3 pages served by FastAPI static files)
- **Database:** SQLite via SQLAlchemy 2.x
- **Charts:** Chart.js 4.x (CDN)
- **ICD-10 reference:** `simple-icd-10` Python package (~14,000 WHO codes, in-memory)
- **CPT reference:** Hand-written `cpt_codes.csv` (~200 SA-specific codes)

---

## Project Structure

```
claimguard/
├── backend/
│   ├── main.py                  # FastAPI app, mounts /static
│   ├── run.py                   # Starts uvicorn from correct CWD
│   ├── requirements.txt
│   ├── routers/
│   │   ├── validate.py          # POST /api/validate, GET /api/sessions/{id}/results
│   │   ├── corrections.py       # POST /api/sessions/{id}/corrections
│   │   ├── export.py            # GET  /api/sessions/{id}/export
│   │   └── dashboard.py         # GET  /api/dashboard
│   ├── validators/
│   │   ├── icd_validator.py     # Normalize + exact match + difflib fuzzy
│   │   ├── cpt_validator.py     # Exact match + difflib fuzzy
│   │   ├── modifier_validator.py # SA approved modifier set check
│   │   └── duplicate_checker.py # PatientID + CPT + Date seen-set check
│   ├── database/
│   │   ├── db.py                # SQLite engine, SessionLocal
│   │   ├── models.py            # ClaimSession, ClaimRow, RefICD, RefCPT
│   │   └── seed.py              # Populates RefICD from simple-icd-10, RefCPT from CSV
│   └── data/
│       └── cpt_codes.csv
└── frontend/
    ├── index.html
    ├── results.html
    ├── dashboard.html
    ├── js/  upload.js  results.js  dashboard.js
    └── css/ styles.css
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/validate` | Upload CSV → session ID + validation rows |
| GET | `/api/sessions/{id}/results` | Paginated rows with flags (page, page_size) |
| POST | `/api/sessions/{id}/corrections` | Save user-selected code corrections |
| GET | `/api/sessions/{id}/export` | Download corrected CSV |
| GET | `/api/dashboard` | Aggregated stats + recent sessions |

---

## Validation Pipeline (per row)

1. **CSV format check** — required columns: `ClaimID, Age, Gender, ICD_Code, CPT_Code, Modifier, Date_of_Service`
2. **ICD code** — strip whitespace + add missing decimal → green auto-fix; difflib top-3 → yellow; no match → red
3. **CPT code** — exact match → green; difflib top-3 → yellow; no match → red
4. **Modifier** — SA approved modifier set (0001–0072); missing → yellow; unknown → red
5. **Duplicate** — same PatientID + CPT_Code + Date_of_Service in-session → red

Row status = worst status across all checks.

---

## Database Schema

### `claim_sessions`
| Column | Type |
|--------|------|
| id | INTEGER PK |
| filename | TEXT |
| uploaded_at | DATETIME |
| total_rows | INTEGER |
| auto_fixed_count | INTEGER |
| manual_count | INTEGER |
| rejected_count | INTEGER |

### `claim_rows`
| Column | Type |
|--------|------|
| id | INTEGER PK |
| session_id | INTEGER (FK) |
| row_number | INTEGER |
| raw_data | JSON |
| status | TEXT (green/yellow/red) |
| issues | JSON (list of {field, message, suggestions}) |
| corrections | JSON (dict of field → corrected value) |

### `reference_icd` / `reference_cpt`
| Column | Type |
|--------|------|
| id | INTEGER PK |
| code | TEXT UNIQUE |
| description | TEXT |

---

## Startup

```bash
cd claimguard/backend
pip install -r requirements.txt
python run.py
# App available at http://localhost:8000
```

On first start, `seed.py` populates `reference_icd` from `simple-icd-10` package and `reference_cpt` from `cpt_codes.csv`. Subsequent starts skip seeding (idempotent check).

---

## Color Coding

| Status | Meaning | User Action |
|--------|---------|-------------|
| Green | Valid or auto-fixed | None required |
| Yellow | Suggestion available | Select from dropdown |
| Red | Manual review required | Review and correct manually |

---

## Key Design Decisions

- Reference codes loaded into DB once at startup; validators receive pre-fetched sets for O(1) lookup per row
- `difflib.get_close_matches` used for fuzzy suggestions (cutoff=0.6, n=3)
- Auto-fixes stored in `ClaimRow.corrections`; export applies corrections on top of `raw_data`
- ICD normalization: strip whitespace, uppercase, insert missing decimal (e.g. `A999` → `A99.9`)
- StaticFiles mounted at `/` after API routes so `/api/...` routes take precedence
