from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..database.models import ClaimRow

router = APIRouter()


@router.post("/api/sessions/{session_id}/corrections")
def save_corrections(session_id: int, corrections: dict, db: Session = Depends(get_db)):
    for row_id_str, field_corrections in corrections.items():
        row = db.query(ClaimRow).filter(
            ClaimRow.id == int(row_id_str),
            ClaimRow.session_id == session_id,
        ).first()
        if row:
            row.corrections = {**(row.corrections or {}), **field_corrections}
    db.commit()
    return {"status": "ok"}
