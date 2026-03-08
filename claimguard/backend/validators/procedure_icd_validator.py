def validate_procedure_icd(procedure_code: str, icd_code: str, rules: dict) -> dict:
    if not procedure_code or not icd_code:
        return {"status": "green", "issue": ""}
    prefixes = rules.get(procedure_code.strip())
    if prefixes is None:
        return {"status": "green", "issue": ""}
    if any(icd_code.strip().upper().startswith(p.upper()) for p in prefixes):
        return {"status": "green", "issue": ""}
    allowed = ", ".join(sorted(prefixes))
    return {
        "status": "yellow",
        "issue": f"Procedure {procedure_code} expects an ICD code starting with [{allowed}]; got {icd_code}",
    }
