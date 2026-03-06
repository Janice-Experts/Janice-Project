import io
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..database.models import ClaimSession, ClaimRow, RefICD, RefCPT
from ..validators.icd_validator import validate_icd
from ..validators.cpt_validator import validate_cpt
from ..validators.modifier_validator import validate_modifier
from ..validators.duplicate_checker import check_duplicate

router = APIRouter()

REQUIRED_COLUMNS = [
    "ClaimID", "Age", "Gender", "ICD_Code", "CPT_Code", "Modifier", "Date_of_Service"
]


@router.post("/api/validate")
async def validate_claims(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content), dtype=str)
    except Exception as e:
        raise HTTPException(400, f"Invalid CSV: {e}")

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise HTTPException(400, f"Missing required columns: {missing_cols}")

    # Load all reference codes once to avoid per-row DB queries
    icd_valid = {r.code for r in db.query(RefICD).all()}
    icd_list = list(icd_valid)
    cpt_valid = {r.code for r in db.query(RefCPT).all()}
    cpt_list = list(cpt_valid)

    session = ClaimSession(filename=file.filename or "upload.csv", total_rows=len(df))
    db.add(session)
    db.flush()

    seen_duplicates: set = set()
    auto_fixed_count = 0
    manual_count = 0
    rejected_count = 0
    row_results = []

    for idx, row in df.iterrows():
        row_dict = {k: ("" if pd.isna(v) else str(v)) for k, v in row.to_dict().items()}
        issues = []
        auto_fixed = {}
        worst_status = "green"

        # ICD validation
        icd_result = validate_icd(row_dict.get("ICD_Code", ""), icd_valid, icd_list)
        if icd_result["status"] == "green" and icd_result.get("auto_fixed"):
            auto_fixed["ICD_Code"] = icd_result["code"]
            issues.append({"field": "ICD_Code", "message": f"Auto-fixed: {icd_result['auto_fixed']}", "suggestions": []})
        elif icd_result["status"] == "yellow":
            issues.append({
                "field": "ICD_Code",
                "message": icd_result.get("issue", "Invalid ICD code"),
                "suggestions": icd_result.get("suggestions", []),
            })
            worst_status = "yellow"
        elif icd_result["status"] == "red":
            issues.append({"field": "ICD_Code", "message": icd_result.get("issue", "Invalid ICD code"), "suggestions": []})
            worst_status = "red"

        # CPT validation
        cpt_result = validate_cpt(row_dict.get("CPT_Code", ""), cpt_valid, cpt_list)
        if cpt_result["status"] == "green" and cpt_result.get("auto_fixed"):
            auto_fixed["CPT_Code"] = cpt_result["code"]
            issues.append({"field": "CPT_Code", "message": f"Auto-fixed: {cpt_result['auto_fixed']}", "suggestions": []})
        elif cpt_result["status"] == "yellow":
            issues.append({
                "field": "CPT_Code",
                "message": cpt_result.get("issue", "Invalid CPT code"),
                "suggestions": cpt_result.get("suggestions", []),
            })
            if worst_status == "green":
                worst_status = "yellow"
        elif cpt_result["status"] == "red":
            issues.append({"field": "CPT_Code", "message": cpt_result.get("issue", "Invalid CPT code"), "suggestions": []})
            worst_status = "red"

        # Modifier validation
        mod_result = validate_modifier(row_dict.get("Modifier", ""))
        if mod_result["status"] == "yellow":
            issues.append({"field": "Modifier", "message": mod_result.get("issue", "Invalid modifier"), "suggestions": []})
            if worst_status == "green":
                worst_status = "yellow"
        elif mod_result["status"] == "red":
            issues.append({"field": "Modifier", "message": mod_result.get("issue", "Invalid modifier"), "suggestions": []})
            worst_status = "red"

        # Duplicate check
        if check_duplicate(row_dict, seen_duplicates):
            issues.append({
                "field": "Duplicate",
                "message": "Duplicate claim: same PatientID, CPT, and Date",
                "suggestions": [],
            })
            worst_status = "red"

        if worst_status == "green":
            if auto_fixed:
                auto_fixed_count += 1
        elif worst_status == "yellow":
            manual_count += 1
        else:
            rejected_count += 1

        claim_row = ClaimRow(
            session_id=session.id,
            row_number=int(idx) + 2,
            raw_data=row_dict,
            status=worst_status,
            issues=issues,
            corrections=auto_fixed,
        )
        db.add(claim_row)
        db.flush()

        row_results.append({
            "id": claim_row.id,
            "row": int(idx) + 2,
            "claim_id": row_dict.get("ClaimID", ""),
            "status": worst_status,
            "issues": issues,
            "auto_fixed": {k: f"{row_dict.get(k, '')} \u2192 {v}" for k, v in auto_fixed.items()},
        })

    session.auto_fixed_count = auto_fixed_count
    session.manual_count = manual_count
    session.rejected_count = rejected_count
    db.commit()

    return {
        "session_id": session.id,
        "filename": session.filename,
        "total_rows": session.total_rows,
        "auto_fixed_count": auto_fixed_count,
        "manual_count": manual_count,
        "rejected_count": rejected_count,
        "rows": row_results,
    }


@router.get("/api/sessions/{session_id}/results")
def get_results(
    session_id: int,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    session = db.query(ClaimSession).filter(ClaimSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    total = db.query(ClaimRow).filter(ClaimRow.session_id == session_id).count()
    rows = (
        db.query(ClaimRow)
        .filter(ClaimRow.session_id == session_id)
        .order_by(ClaimRow.row_number)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "session_id": session_id,
        "filename": session.filename,
        "total": total,
        "page": page,
        "page_size": page_size,
        "auto_fixed_count": session.auto_fixed_count,
        "manual_count": session.manual_count,
        "rejected_count": session.rejected_count,
        "rows": [
            {
                "id": r.id,
                "row": r.row_number,
                "claim_id": r.raw_data.get("ClaimID", ""),
                "status": r.status,
                "issues": r.issues,
                "corrections": r.corrections,
                "raw_data": r.raw_data,
            }
            for r in rows
        ],
    }
