import difflib


def validate_cpt(code: str, valid_codes: set, code_list: list) -> dict:
    original = code.strip() if code else ""
    if not original or original.lower() == "nan":
        return {"status": "red", "issue": "CPT code is empty"}

    if original in valid_codes:
        return {"status": "green", "auto_fixed": None, "code": original}

    suggestions = difflib.get_close_matches(original, code_list, n=3, cutoff=0.6)
    if suggestions:
        return {
            "status": "yellow",
            "suggestions": suggestions,
            "code": original,
            "issue": f"Unknown CPT code '{original}'",
        }
    return {"status": "red", "code": original, "issue": f"Unknown CPT code '{original}', no suggestions found"}
