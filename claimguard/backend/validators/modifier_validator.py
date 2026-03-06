SA_APPROVED_MODIFIERS = {
    "0001", "0002", "0003", "0004", "0005", "0006", "0007", "0008", "0009", "0010",
    "0011", "0012", "0013", "0014", "0015", "0016", "0017", "0018", "0019", "0020",
    "0021", "0022", "0023", "0024", "0025", "0026", "0027", "0028", "0029", "0030",
    "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040",
    "0041", "0042", "0043", "0044", "0045", "0050", "0051", "0052", "0053", "0054",
    "0055", "0060", "0061", "0062", "0070", "0071", "0072",
}


def validate_modifier(modifier: str) -> dict:
    m = str(modifier).strip() if modifier else ""
    if not m or m.lower() == "nan":
        return {"status": "yellow", "issue": "Missing modifier"}
    if m in SA_APPROVED_MODIFIERS:
        return {"status": "green"}
    return {"status": "red", "issue": f"Modifier '{m}' not in SA approved list"}
