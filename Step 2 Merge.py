# ======================================
# MIMIC-III MERGE SCRIPT (Memory-Safe)
# ======================================
#Merges ICU stays with Admissions, Diagnosis and Patients and the selected Labevents and vitals from prev. scripts. 

"""
Data source: Johnson, A., Pollard, T., & Mark, R. (2016). MIMIC-III Clinical Database (version 1.4). 
PhysioNet. RRID:SCR_007345. https://doi.org/10.13026/C2XW26
"""
import pandas as pd
import os


# -------------------------------
#  CONFIG 
# -------------------------------
data_path = "RAWDATA/"

#output file
output_dir = "Data"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "Step2_merged.csv")

#input files 
patients_file = os.path.join(data_path, "PATIENTS.csv")
admissions_file = os.path.join(data_path, "ADMISSIONS_cleaned.csv")
icustays_file = os.path.join(data_path, "ICUSTAYS.csv")
vitals_file = os.path.join(output_dir, "Step1a_first_vitals.csv")   
labs_file = os.path.join(output_dir, "Step1b_first_labs.csv")  
diagnoses_icd_file = os.path.join("C:/Users/vibek/.vscode/DATA/MIMICIII/DIAGNOSES_ICD.csv.gz")


#    LOAD CORE TABLES 
# -------------------------------

patients = pd.read_csv(patients_file)
admissions = pd.read_csv(admissions_file)
icustays = pd.read_csv(icustays_file)
vitals = pd.read_csv(vitals_file)
labs = pd.read_csv(labs_file, low_memory=False) 
diagnoses_icd = pd.read_csv(
    diagnoses_icd_file,
    dtype=str
)
# Load ICD‑9 dictionary for text descriptions
icd_dict = pd.read_csv(
    os.path.join(data_path, "D_ICD_DIAGNOSES.csv"),
    dtype=str
)

print("✔ Loaded PATIENTS, ADMISSIONS, ICUSTAYS, VITALS, LABS, DIAGNOSES_ICD")

# -------------------------------
# CLEAN + STANDARDIZE
# -------------------------------

# Rename free‑text diagnosis column
admissions = admissions.rename(columns={"DIAGNOSIS": "initial_DIAGNOSIS"})
print("✔ Renamed DIAGNOSIS field from hopsital admissions → initial_DIAGNOSIS")

# Parse datetime columns for admissions
for col in ["ADMITTIME", "DISCHTIME", "DEATHTIME"]:
    if col in admissions.columns:
        admissions[col] = pd.to_datetime(admissions[col], errors="coerce")

# Parse ICU time columns
icustays["INTIME"] = pd.to_datetime(icustays["INTIME"], errors="coerce")
icustays["OUTTIME"] = pd.to_datetime(icustays["OUTTIME"], errors="coerce")
print("✔ Parsed datetime columns")


# STANDARDIZE ID TYPES (prevents SUBJECT_ID_x / SUBJECT_ID_y)


# Tables with both SUBJECT_ID and HADM_ID
for df in [icustays, labs, admissions]:
    df["SUBJECT_ID"] = pd.to_numeric(df["SUBJECT_ID"], errors="coerce").astype("Int64")
    df["HADM_ID"] = pd.to_numeric(df["HADM_ID"], errors="coerce").astype("Int64")

# PATIENTS has SUBJECT_ID only
patients["SUBJECT_ID"] = pd.to_numeric(patients["SUBJECT_ID"], errors="coerce").astype("Int64")

print("✔ Standardized SUBJECT_ID and HADM_ID types")

# Drop ROW_ID if present (to avoid duplicate ROW_ID columns after merging)
for df in [icustays, vitals, labs, admissions, patients]:
    if "ROW_ID" in df.columns:
        df.drop(columns=["ROW_ID"], inplace=True)

print("✔ Removed ROW_ID columns")

# --------------------------------------------------------------
#    START MERGE WITH ICUSTAY AS THE BASE 
# --------------------------------------------------------------

icu_summary = icustays.copy()


#    MERGE WITH PATIENTS 
icu_summary = icu_summary.merge(patients, on="SUBJECT_ID", how="left")
print("✔ Merged ICUSTAYS with PATIENTS")


#   MERGE WITH ADMISSIONS 
icu_summary = icu_summary.merge(admissions, on=["HADM_ID", "SUBJECT_ID"], how="left")
print("✔ Merged ICUSTAYS with ADMISSIONS")

#    MERGE VITALS  
icu_summary = icu_summary.merge(
    vitals,
    on=["ICUSTAY_ID"],  
    how="left"
)
print("✔ Merged ICUSTAYS with VITALS")

# MERGE LABS 
icu_summary = icu_summary.merge(
    labs, 
    on=["ICUSTAY_ID", "HADM_ID", "SUBJECT_ID"],
    how="left"
)
print("✔ Merged ICUSTAYS with LABS")




# ======================================
#  ICD9 DICTIONARY
# ======================================

# Convert HADM_ID to numeric
diagnoses_icd["HADM_ID"] = pd.to_numeric(diagnoses_icd["HADM_ID"], errors="coerce").astype("Int64")


#Make sure to drop superfluous ICUSTAYS columns from diagnoses_icd to avoid duplicates when merging with icu_summary
icu_cols = [
    "DBSOURCE", "FIRST_CAREUNIT", "LAST_CAREUNIT",
    "FIRST_WARDID", "LAST_WARDID",
    "INTIME", "OUTTIME", "LOS"
]

diagnoses_icd = diagnoses_icd.drop(columns=[c for c in icu_cols if c in diagnoses_icd.columns], errors="ignore")


# ======================================
#  STRING OF ALL ICD‑9 CODES PER HADM_ID
# ======================================

diagnoses_grouped = (
    diagnoses_icd
    .dropna(subset=["ICD9_CODE"])
    .groupby("HADM_ID")["ICD9_CODE"]
    .apply(lambda x: "; ".join(sorted(x.unique())))
    .reset_index()
    .rename(columns={"ICD9_CODE": "ICD9_CODES"})
)

print("✔ Created ICD9_CODES (all ICD‑9 codes per admission)")


# ======================================
#  PRINCIPAL ICD‑9 CODE + TEXT
# ======================================

principal_dx = diagnoses_icd[diagnoses_icd["SEQ_NUM"] == "1"].copy()
icu_cols = [
    "SUBJECT_ID", 
    "DBSOURCE", "FIRST_CAREUNIT", "LAST_CAREUNIT",
    "FIRST_WARDID", "LAST_WARDID",
    "INTIME", "OUTTIME", "LOS"
]
# Drop ICU-level columns from principal_dx to avoid duplicates
principal_dx = principal_dx.drop(columns=[c for c in icu_cols if c in principal_dx.columns], errors="ignore")


# # Merge text descriptions for principal ICD‑9 codes
principal_dx = principal_dx.merge(
    icd_dict[["ICD9_CODE", "SHORT_TITLE"]],
    on="ICD9_CODE",
    how="left"
)

principal_dx.rename(columns={
    "ICD9_CODE": "ICD9_primary",
    "SHORT_TITLE": "ICD9_primary_title"
}, inplace=True)


print("✔ Extracted principal ICD‑9 code + title")


from config.groupings.icd9 import icd9_parent, infer_parent_from_initial

principal_dx["ICD9_parent"] = principal_dx["ICD9_primary"].apply(icd9_parent)

print("✔ Assigned ICD9_parent category")

# -------------------------------
#   RENAME TIME COLUMNS 
# -------------------------------
icu_summary = icu_summary.rename(columns={
    "ADMITTIME": "ADMITTIME_HADM",
    "DISCHTIME": "DISCHTIME_HADM",
    "INTIME": "INTIME_ICU",
    "OUTTIME": "OUTTIME_ICU"
})

# ======================================
# MERGE ALL ICD‑9 INFO INTO MAIN DATASET
# ======================================

icu_summary = icu_summary.merge(diagnoses_grouped, on="HADM_ID", how="left")
icu_summary = icu_summary.merge(principal_dx, on="HADM_ID", how="left")

print("✔ Merged ICD‑9 codes into dataset")


# ======================================
# FALLBACK: USE INITIAL_DIAGNOSIS IF ICD9_primary IS MISSING
# ======================================


mask_missing = icu_summary["ICD9_primary"].isna()
icu_summary.loc[mask_missing, "ICD9_parent"] = (
    icu_summary.loc[mask_missing, "initial_DIAGNOSIS"].apply(infer_parent_from_initial)
)

print("✔ Applied fallback ICD9_parent from initial diagnosis")


# -------------------------------
#        SAVE FINAL DATASET 
# -------------------------------
icu_summary = icu_summary.drop(columns=["SEQ_NUM"], errors="ignore")


icu_summary.to_csv(output_file, index=False)

print(f"✅ Final merged dataset saved to: {output_file}")

# -------------------------------
#        PRINT FEATURES  
# -------------------------------
print("\n=== Features in final dataset ===")
# print(list(icu_summary.columns))

print(f"\nFinal dataset: {len(icu_summary)} rows, {icu_summary['SUBJECT_ID'].nunique()} unique patients")
vars_to_check = [
    "HEARTRATE", "SYSTOLIC", "DIASTOLIC", "RESP", "SPO2", "HEIGHT_raw", "WEIGHT",
    "ALBUMIN",
    "BLOOD_UREA_NITRO",
    "CHOLESTEROL",
    "Creatinine",
    "GLUCOSE_BLOOD",
    "HEMOGLOBIN",
    "NT-proBNP",
    "POTASSIUM",
    "SODIUM"
]

missing = pd.DataFrame({
    "missing_count":   icu_summary[vars_to_check].isna().sum(),
    "missing_percent": icu_summary[vars_to_check].isna().mean() * 100
})
print("=== Missing numerical values overview — adult population ===")
print(missing)