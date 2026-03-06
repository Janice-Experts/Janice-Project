import re
import difflib


def _normalize_icd(code: str) -> str:
    code = code.strip().upper()
    clean = re.sub(r"[^A-Z0-9]", "", code)
    # e.g. A999 -> A99.9, B1234 -> B12.34
    if re.match(r"^[A-Z]\d{3,}$", clean):
        code = clean[:3] + "." + clean[3:]
    else:
        code = clean
    return code


def validate_icd(code: str, valid_codes: set, code_list: list) -> dict:
    original = code.strip() if code else ""
    if not original or original.lower() == "nan":
        return {"status": "red", "issue": "ICD code is empty"}

    normalized = _normalize_icd(original)

    if normalized in valid_codes:
        if normalized != original.upper().strip():
            return {"status": "green", "auto_fixed": f"{original} \u2192 {normalized}", "code": normalized}
        return {"status": "green", "auto_fixed": None, "code": normalized}

    suggestions = difflib.get_close_matches(normalized, code_list, n=3, cutoff=0.6)
    if suggestions:
        return {
            "status": "yellow",
            "suggestions": suggestions,
            "code": original,
            "issue": f"Unknown ICD code '{original}'",
        }
    return {"status": "red", "code": original, "issue": f"Unknown ICD code '{original}', no suggestions found"}
