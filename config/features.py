# config/features.py
# -------------------------------------------------------
# Feature lists and schema definitions for the mini dataset
# -------------------------------------------------------

ID_COLS          = ["subject_id", "icustay_id"]
BOOLEAN_COLS     = ["readmission", "prior_icu", "gender"]
DEMOGRAPHIC_COLS = ["age"]
CATEGORICAL_COLS = ["admission_type", "first_careunit", "ethnicity", "icd9"]
ORDINAL_COLS     = ["bmi", "nt-probnp", "cholesterol", "albumin"]
MEASUREMENT_COLS = [
    "glucose", "sodium", "spo2", "respiratory_rate",
    "heartrate", "systolic_bp", "diastolic_bp", "blood_urea_nitro",
]

FLOAT64_COLS = ["creatinine", "potassium", "hemoglobin"]
SOCIAL_COLS  = ["insurance", "language", "religion", "marital_status"]

FEATURES_TO_USE = (
    ID_COLS + BOOLEAN_COLS + DEMOGRAPHIC_COLS + CATEGORICAL_COLS +
    ORDINAL_COLS + MEASUREMENT_COLS + FLOAT64_COLS ) #+ SOCIAL_COLS

# dtype groups for schema enforcement
INT8_COLS  = BOOLEAN_COLS + ORDINAL_COLS
INT64_COLS = MEASUREMENT_COLS + DEMOGRAPHIC_COLS
IGNORE_COLS = []

RENAME_DICT = {
    "SUBJECT_ID":       "subject_id",
    "ICUSTAY_ID":       "icustay_id",
    "READMISSION":      "readmission",
    "AGE":              "age",
    "ETHNICITY_GROUP":  "ethnicity",
    "ADMISSION_TYPE":   "admission_type",
    "Creatinine":       "creatinine",
    "BLOOD_UREA_NITRO": "blood_urea_nitro",
    "POTASSIUM":        "potassium",
    "RESP":             "respiratory_rate",
    "HEARTRATE":        "heartrate",
    "NT":               "nt-probnp",
    "CHOL":             "cholesterol",
    "SYSTOLIC":         "systolic_bp",
    "DIASTOLIC":        "diastolic_bp",
    "ALB":              "albumin",
    "HEMOGLOBIN":       "hemoglobin",
    "BMI":              "bmi",
    "SODIUM":           "sodium",
    "PRIOR_ICU":        "prior_icu",
    "ICD9_parent":      "icd9",
    "SPO2":             "spo2",
    "GENDER":           "gender",
    "GLUCOSE_BLOOD":    "glucose",
    "FIRST_CAREUNIT":   "first_careunit",
    "INSURANCE":        "insurance",
    "LANGUAGE_GROUP":   "language",
    "RELIGION_GROUP":   "religion",
    "MARITAL_GROUP":    "marital_status",
}

GENDER_MAP = {
    "M": 0, "m": 0, "male": 0, "Male": 0,
    "F": 1, "f": 1, "female": 1, "Female": 1
}



