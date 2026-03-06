from fastapi import APIRouter, Depends
from sqlalchemy import func, cast, Text
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..database.models import ClaimSession, ClaimRow

router = APIRouter()


@router.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    sessions = (
        db.query(ClaimSession)
        .order_by(ClaimSession.uploaded_at.desc())
        .limit(10)
        .all()
    )

    total_claims = db.query(func.sum(ClaimSession.total_rows)).scalar() or 0
    total_auto_fixed = db.query(func.sum(ClaimSession.auto_fixed_count)).scalar() or 0
    total_manual = db.query(func.sum(ClaimSession.manual_count)).scalar() or 0
    total_rejected = db.query(func.sum(ClaimSession.rejected_count)).scalar() or 0

    icd_errors = (
        db.query(ClaimRow)
        .filter(cast(ClaimRow.issues, Text).like('%"ICD_Code"%'))
        .count()
    )
    cpt_errors = (
        db.query(ClaimRow)
        .filter(cast(ClaimRow.issues, Text).like('%"CPT_Code"%'))
        .count()
    )
    modifier_errors = (
        db.query(ClaimRow)
        .filter(cast(ClaimRow.issues, Text).like('%"Modifier"%'))
        .count()
    )
    duplicate_errors = (
        db.query(ClaimRow)
        .filter(cast(ClaimRow.issues, Text).like('%"Duplicate"%'))
        .count()
    )

    return {
        "summary": {
            "total_claims": total_claims,
            "auto_fixed": total_auto_fixed,
            "needs_review": total_manual,
            "rejected": total_rejected,
        },
        "error_breakdown": {
            "invalid_icd": icd_errors,
            "invalid_cpt": cpt_errors,
            "bad_modifier": modifier_errors,
            "duplicates": duplicate_errors,
        },
        "recent_sessions": [
            {
                "id": s.id,
                "filename": s.filename,
                "uploaded_at": s.uploaded_at.isoformat(),
                "total_rows": s.total_rows,
                "auto_fixed_count": s.auto_fixed_count,
                "manual_count": s.manual_count,
                "rejected_count": s.rejected_count,
            }
            for s in sessions
        ],
    }
