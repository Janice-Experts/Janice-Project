def check_duplicate(row_data: dict, seen: set) -> bool:
    patient_id = str(row_data.get("PatientID", "")).strip()
    cpt_code = str(row_data.get("CPT_Code", "")).strip()
    date_of_service = str(row_data.get("Date_of_Service", "")).strip()

    if not patient_id or patient_id.lower() == "nan":
        return False

    key = (patient_id, cpt_code, date_of_service)
    if key in seen:
        return True
    seen.add(key)
    return False
