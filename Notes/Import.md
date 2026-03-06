# ClaimGuard SA MVP - Business Requirements Document

## Project Overview
ClaimGuard is a **web-based tool** designed to reduce claim rejections caused by ICD/CPT coding errors, missing modifiers, and duplicates in South African clinics and billing companies.  
The MVP enables users to **validate claims before submission**, auto-fix safe errors, suggest corrections, and provide a dashboard with analytics.

---

## Objectives
- Prevent claim rejections due to coding/modifier errors.
- Save administrative staff time by automating validation.
- Provide a simple interface for clinics.
- Generate corrected CSVs ready for upload to billing systems.
- Track recurring errors with dashboard analytics.

---

## Scope

**In-Scope:**
- Upload CSV files with claim data.
- Validate ICD and CPT codes.
- Check for missing/incorrect modifiers.
- Detect duplicate claims.
- Auto-fix simple errors and provide suggestions.
- Export corrected CSVs.
- Dashboard summarizing errors and auto-fixes.
- Minimal patient data storage (age, gender, optional ID).

**Out-of-Scope:**
- Direct insurer API integration.
- Complex pre-authorization logic.
- Multi-insurer-specific rules.

---

## Functional Requirements

### CSV Upload & Validation
- Required CSV columns: `ClaimID, PatientID (optional), Age, Gender, ICD_Code, CPT_Code, Modifier, Date_of_Service`.
- Validation checks:
  - ICD code exists in reference table.
  - CPT code exists in reference table.
  - Modifier is valid (if present).
  - Duplicate claims (same PatientID, CPT, Date).
- Issue flagging:
  - Green: auto-fixed.
  - Yellow: suggestion dropdown.
  - Red: manual review.

### Suggestions & Auto-Fix
- Auto-fix minor formatting errors.
- Suggest alternative ICD/CPT codes when invalid.
- Provide dropdown for user to manually select correct codes.

### Export
- Download corrected CSV after validation.

### Dashboard
- Total claims processed.
- Error types (Invalid ICD, Invalid CPT, Invalid Modifier, Duplicates).
- Auto-fix vs manual review counts.
- Bar charts visualization.

---

## Non-Functional Requirements
- Web-based, browser-accessible.
- Backend: Python 3.10+, FastAPI.
- Frontend: HTML + JavaScript.
- Database: minimal, SQLite acceptable.
- Security: minimal patient info, POPIA compliant.
- Performance: handle 1000+ claims per batch efficiently.

---

## Validation Rules

| Rule | Description |
|------|------------|
| ICD Code | Must exist in reference table; auto-fix minor formatting; suggest alternatives. |
| CPT Code | Must exist in reference table; suggest alternatives. |
| Modifier | Must be approved; flag missing/incorrect. |
| Duplicates | Same PatientID + CPT + Date flagged. |
| CSV Format | Required columns must exist. |

---

## Workflow
1. User uploads CSV.
2. Backend validates claims.
3. Validation report generated (color-coded).
4. User reviews yellow/red flags; selects corrections.
5. Corrected CSV exported.
6. Dashboard updated.

---

## System Architecture
