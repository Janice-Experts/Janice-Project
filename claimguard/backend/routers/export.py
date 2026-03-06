import io
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..database.models import ClaimRow, ClaimSession

router = APIRouter()


@router.get("/api/sessions/{session_id}/export")
def export_csv(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ClaimSession).filter(ClaimSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    rows = (
        db.query(ClaimRow)
        .filter(ClaimRow.session_id == session_id)
        .order_by(ClaimRow.row_number)
        .all()
    )
    if not rows:
        raise HTTPException(404, "No rows found for session")

    records = []
    for row in rows:
        data = dict(row.raw_data)
        if row.corrections:
            data.update(row.corrections)
        records.append(data)

    df = pd.DataFrame(records)
    output = io.StringIO()
    df.to_csv(output, index=False)

    filename = f"corrected_{session.filename or 'claims.csv'}"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
