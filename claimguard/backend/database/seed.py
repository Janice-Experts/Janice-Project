import csv
import os
from sqlalchemy.orm import Session
from .models import RefICD, RefCPT

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def seed_reference_data(db: Session) -> None:
    if db.query(RefICD).first() is None:
        _load_icd(db)
    if db.query(RefCPT).first() is None:
        _load_cpt(db)


def _load_icd(db: Session) -> None:
    import simple_icd_10 as icd10
    codes = icd10.get_all_codes(with_dots=True)
    for code in codes:
        desc = icd10.get_description(code)
        db.add(RefICD(code=code.upper(), description=desc or ""))
    db.commit()


def _load_cpt(db: Session) -> None:
    path = os.path.join(DATA_DIR, "cpt_codes.csv")
    if not os.path.exists(path):
        return
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            db.add(RefCPT(code=row["code"].strip(), description=row["description"].strip()))
    db.commit()
