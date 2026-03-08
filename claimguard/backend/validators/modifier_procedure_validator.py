def validate_modifier_procedure(modifier: str, procedure_code: str, blocked: set) -> dict:
    if not modifier or not procedure_code:
        return {"status": "green", "issue": ""}
    if (modifier.strip(), procedure_code.strip()) in blocked:
        return {
            "status": "yellow",
            "issue": f"Modifier {modifier} is not valid with procedure code {procedure_code}",
        }
    return {"status": "green", "issue": ""}
