from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float
from .db import Base


class ClaimSession(Base):
    __tablename__ = "claim_sessions"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    total_rows = Column(Integer, default=0)
    auto_fixed_count = Column(Integer, default=0)
    manual_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)


class ClaimRow(Base):
    __tablename__ = "claim_rows"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, index=True)
    row_number = Column(Integer)
    raw_data = Column(JSON)
    status = Column(String)  # green / yellow / red
    issues = Column(JSON, default=list)
    corrections = Column(JSON, default=dict)


class RefICD(Base):
    __tablename__ = "reference_icd"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    description = Column(String)


class RefCPT(Base):
    __tablename__ = "reference_cpt"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    description = Column(String)
