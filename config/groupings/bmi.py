# cleaning/groupings/bmi.py

import pandas as pd

# BMI category order
BMI_LABELS = [
    "Missing",
    "Underweight",
    "Normal",
    "High",
    "Obese",
    "Morbidly obese"
]

BMI_DTYPE = pd.CategoricalDtype(
    categories=BMI_LABELS,
    ordered=True
)

# -----------------------------------------
# ADULT  BMI CLASSIFICATION
# -----------------------------------------

# ICD-9 groups
MORBID_OBESITY_CODES = {
    "V8541",  # BMI 40.0-44.9
    "V8542",  # BMI 45.0-49.9
    "V8543",  # BMI 50.0-59.9
    "V8544",  # BMI 60.0-69.9
    "V8545",  # BMI 70 and over
    "27801",    # Morbid obesity diagnosis that histporically was tied to lower bmi --> consistent to Obese category. 
    "27803",   # Obesity hypoventilation syndrome
}

OBESITY_CODES = {
    "V8530",  # BMI 30.0-30.9
    "V8531",  # BMI 31.0-31.9
    "V8532",  # BMI 32.0-32.9
    "V8533",  # BMI 33.0-33.9
    "V8534",  # BMI 34.0-34.9
    "V8535",  # BMI 35.0-35.9
    "V8536",  # BMI 36.0-36.9
    "V8537",  # BMI 37.0-37.9
    "V8538",  # BMI 38.0-38.9
    "V8539",  # BMI 39.0-39.9
    "27800",   # Obesity unspecified
        
}

OVERWEIGHT_CODES = {
    "V8521",  # BMI 25.0-25.9
    "V8522",  # BMI 26.0-26.9
    "V8523",  # BMI 27.0-27.9
    "V8524",  # BMI 28.0-28.9
    "V8525",  # BMI 29.0-29.9
    "27802"   # Overweight diagnosis
}

NORMAL_WEIGHT_CODES = {
    "V851",   # BMI 19-24, adult
}

UNDERWEIGHT_CODES = {
    "V850",   # BMI less than 19, adult
    "78322",  # Underweight
   
}

#ICD9 codes: https://www.cms.gov/medicare/coding-billing/icd-10-codes/icd-9-cm-diagnosis-procedure-codes-abbreviated-and-full-code-titles 


def _classify_bmi_icd(icd_string):
    """Apply ICD-9 code classification — V codes first, then 278.xx."""
    if pd.isna(icd_string):
        return None
    codes = [c.strip() for c in str(icd_string).replace(",", ";").split(";")]

    # Pass 1: V85 codes
    for code_set, category in [
        (MORBID_OBESITY_CODES, "Morbidly obese"),
        (OBESITY_CODES, "Obese"),
        (OVERWEIGHT_CODES, "High"),
        (NORMAL_WEIGHT_CODES, "Normal"),
        (UNDERWEIGHT_CODES, "Underweight"),
    ]:
        if any(code in code_set and code.startswith("V") for code in codes):
            return category

    # Pass 2: 278.xx codes
    for code_set, category in [
        (MORBID_OBESITY_CODES, "Morbidly obese"),
        (OBESITY_CODES, "Obese"),
        (OVERWEIGHT_CODES, "High"),
        (NORMAL_WEIGHT_CODES, "Normal"),
        (UNDERWEIGHT_CODES, "Underweight"),
    ]:
        if any(code in code_set for code in codes):
            return category

    return None


def _classify_bmi_numeric(bmi_value):
    """Apply BMI thresholds — shared by all classification functions."""
    if pd.isna(bmi_value):
        return None
    if bmi_value < 18.5:
        return "Underweight"
    elif bmi_value < 25:
        return "Normal"
    elif bmi_value < 30:
        return "High"
    elif bmi_value < 40:
        return "Obese"
    else:
        return "Morbidly obese"
    


def classify_adult_bmi(bmi_real, icd_string, bmi_calc):
    """Classify BMI using all available information, with priority: 
    1) numeric BMI where actual raw values were present in dataset, 
    2) For all with imputed values: first use ICD-9 codes when these exist, then  
    3) calculated BMI (based on imputed values)."""

    return (
        _classify_bmi_numeric(bmi_real)
        or _classify_bmi_icd(icd_string)
        or _classify_bmi_numeric(bmi_calc)
        or "Missing"
    )


def classify_adult_bmi_codes_only(icd_string):
    return _classify_bmi_icd(icd_string) or "Missing"


def classify_adult_bmi_numbers_only(bmi_value):
    return _classify_bmi_numeric(bmi_value) or "Missing"




#QA HELPERS — remove after inspection

ALL_BMI_CODES = (
    MORBID_OBESITY_CODES | OBESITY_CODES | OVERWEIGHT_CODES | 
    NORMAL_WEIGHT_CODES | UNDERWEIGHT_CODES
)

def extract_bmi_icd(icd_string):
    """Return all BMI-related ICD-9 codes found, or None."""
    if pd.isna(icd_string):
        return None
    codes = [c.strip() for c in str(icd_string).replace(",", ";").split(";")]
    matches = [code for code in codes if code in ALL_BMI_CODES]
    return "; ".join(matches) if matches else None
