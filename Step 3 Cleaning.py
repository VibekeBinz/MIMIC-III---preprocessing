# =============================================
# CLEANING AND FORMATTING PIPELINE FOR MIMIC III 
# =============================================

"""
Data source: Johnson, A., Pollard, T., & Mark, R. (2016). MIMIC-III Clinical Database (version 1.4). 
PhysioNet. RRID:SCR_007345. https://doi.org/10.13026/C2XW26
"""


import pandas as pd
import os
import numpy as np
import re


# -------------------------------
#            CONFIG AND LOAD 
# -------------------------------
output_dir = "Data"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "Step3_genready.csv")
output_file_maxi = os.path.join(output_dir, "Step3_maxi_qa_file.csv")
input_file  = os.path.join(output_dir, "Step2_merged.csv")

print("Loading:", input_file)
df = pd.read_csv(
    input_file,
    parse_dates=["DOB", "DOD", "DOD_HOSP", "DOD_SSN",
                 "ADMITTIME_HADM", "DISCHTIME_HADM", "INTIME_ICU", "OUTTIME_ICU"],
    low_memory=False
)
print(f"✔ Loaded  dataset of merged raw inputs — rows: {len(df)}, columns: {len(df.columns)}")



# ====================================
# AGE CALCULATION  
# ====================================
print("\n=== AGE CALCULATION ===\n")    
# -----------------------------------------
# NEWBORN IDENTIFICATION
# -----------------------------------------
df["AGE_RAW"] = df["INTIME_ICU"].dt.year - df["DOB"].dt.year
df["IS_NEWBORN"] = df["FIRST_CAREUNIT"] == "NICU"
df["AGE"] = np.nan  # initialise cleanly for all rows
df.loc[df["IS_NEWBORN"], "AGE"] = 0
print("✔ Newborns identified from NICU admissions, AGE set to 0.")

# -------------------------------
# ELDERLY AGE SAMPLING (>89)
# -------------------------------
# Patients aged >89 are assigned a synthetic age drawn from a half-Gaussian distribution.
# Parameters and rationale defined in config/imputation.py.

from config.imputation import sample_elderly, ELDERLY_AGE_SEED

mask_old     = (df["AGE_RAW"] > 89) & (~df["IS_NEWBORN"])
old_patients = df[mask_old].sort_values(["SUBJECT_ID", "INTIME_ICU"])
first_stay   = old_patients.groupby("SUBJECT_ID").head(1)

rng     = np.random.default_rng(ELDERLY_AGE_SEED)
sampled = sample_elderly(len(first_stay), rng=rng)
df.loc[first_stay.index, "AGE"] = sampled
print(f"✔ Sampled realistic ages above 89 for {len(first_stay)} unique patients.")

# -----------------------------------------
# PROPAGATE AGE FORWARD FOR LATER ELDERLY STAYS
# -----------------------------------------
for sid, group in old_patients.groupby("SUBJECT_ID"):
    group = group.sort_values("INTIME_ICU")   # ensure chronological order
    rows  = group.index

    first_idx = rows[0]
    base_age  = df.loc[first_idx, "AGE"]
    base_time = df.loc[first_idx, "INTIME_ICU"]

    later_rows = rows[1:]
    if len(later_rows) == 0:
        continue

    age_delta = (df.loc[later_rows, "INTIME_ICU"] - base_time).dt.days / 365.25
    df.loc[later_rows, "AGE"] = (base_age + age_delta).round().astype(int)

print("✔ Propagated age forward for subsequent ICU stays.")


# -----------------------------------------
# AGE CALCULATION FOR NON-ELDERLY ADULTS
# -----------------------------------------
mask_adults = (~df["IS_NEWBORN"]) & (~mask_old)
df.loc[mask_adults, "AGE"] = df.loc[mask_adults, "AGE_RAW"]
print("✔ Calculated age for adults < 90.")


# -------------------------------
# CLEANUP - remove helper column 
# -------------------------------
df.drop(columns=["AGE_RAW"], inplace=True)



# -------------------------------
# QA CHECKS
# -------------------------------
num_unique_age_zero   = df.loc[df["AGE"] == 0, "SUBJECT_ID"].nunique()
num_flagged_newborns  = df.loc[df["IS_NEWBORN"], "SUBJECT_ID"].nunique()
num_missing_age       = df["AGE"].isna().sum()

print("\n=== AGE QA CHECKS ===")
print(f"Total admissions:               {len(df)}")
print(f"Total unique patients:          {df['SUBJECT_ID'].nunique()}")
print(f"Unique patients with AGE = 0:   {num_unique_age_zero}")
print(f"Unique patients flagged NICU:   {num_flagged_newborns}")
# print(f"Rows with missing AGE:          {num_missing_age}")
if num_missing_age > 0:
    print("⚠ WARNING: some rows have missing AGE — check for patients outside all masks")


# ===========================================
# STEP 4a FLAGS AND GROUPINGS 
# ===========================================

print("\n=== CREATE GROUPINGS AND FLAGS ===\n") 

# --------------------------------------------------------------
# DEMOGRAPHIC GROUPINGS
# --------------------------------------------------------------

from config.groupings.demo import apply_demographic_groupings
print("Grouping demographic features...")
df = apply_demographic_groupings(df)
print("✔ Grouping applied to simplify demographic categories.")

# -------------------------------------------------------
# REMOVE ORGAN DONORS (before calculating readmission)
# -------------------------------------------------------

mask_organ = df["initial_DIAGNOSIS"].str.contains("ORGAN DONOR", case=False, na=False)
n_removed = mask_organ.sum()
df = df[~mask_organ].reset_index(drop=True)
print(f"✔ Removed {n_removed} organ donor rows (initial_DIAGNOSIS contains 'ORGAN DONOR') prior to readmission calculation.")  

# -------------------------------
# READMISSION FLAG
# -------------------------------
df = df.sort_values(["SUBJECT_ID", "INTIME_ICU"]).copy()
df["NEXT_INTIME"] = df.groupby("SUBJECT_ID")["INTIME_ICU"].shift(-1)
df["DELTA_DAYS"]  = (df["NEXT_INTIME"] - df["OUTTIME_ICU"]).dt.days
df["READMISSION"] = ((df["DELTA_DAYS"] >= 0) & (df["DELTA_DAYS"] <= 30)).astype(int)
df = df.drop(columns=["NEXT_INTIME", "DELTA_DAYS"])
print("✔ READMISSION flag created for 30-day readmissions to any ICU.")

# -------------------------------
# PRIOR ICU FLAG
# -------------------------------
df = df.sort_values(["SUBJECT_ID", "INTIME_ICU"])
df["PRIOR_ICU"] = (df.groupby("SUBJECT_ID").cumcount() > 0).astype(bool)
print("✔ PRIOR_ICU flag created if patient has had a previous ICU stay.")

# -------------------------------------------------------
# ICUSTAY EXPIRE FLAG
# -------------------------------------------------------
# Organ donors in MIMIC can have DOD_HOSP < INTIME_ICU because the
# ICU admission is for post-mortem organ harvesting. We intentionally
# include these in ICUSTAY_EXPIRE as death-associated stays.

for col in ["INTIME_ICU", "OUTTIME_ICU", "DOD_HOSP"]:
    df[col] = pd.to_datetime(df[col], errors="coerce")

df["INTIME_DATE"]   = df["INTIME_ICU"].dt.normalize()
df["OUTTIME_DATE"]  = df["OUTTIME_ICU"].dt.normalize()
df["DOD_HOSP_DATE"] = df["DOD_HOSP"].dt.normalize()

df["ICUSTAY_EXPIRE"] = (
    (df["EXPIRE_FLAG"] == 1)
    & df["DOD_HOSP_DATE"].notna()
    & (
        ((df["DOD_HOSP_DATE"] >= df["INTIME_DATE"]) & (df["DOD_HOSP_DATE"] <= df["OUTTIME_DATE"]))
        | (df["DOD_HOSP_DATE"] < df["INTIME_DATE"])
    )
).astype(int)

df = df.drop(columns=["DOD_HOSP_DATE", "INTIME_DATE", "OUTTIME_DATE"], errors="ignore")
print("✔ ICUSTAY_EXPIRE flag created")

# --------------------------------------------------------------------
# COHORT DEFINITION
# --------------------------------------------------------------------
print("\n=== DEFINING COHORT... ===\n") 

# -------------------------------------------------------
# REMOVE ICU-EXPIRED STAYS AND NEWBORNS 
# -------------------------------------------------------

from config.cohort import (
    remove_icu_expired,
    remove_newborns, remove_missing_rows,
)
# in the cohort-definition section:
df = remove_icu_expired(df)
df = remove_newborns(df)



print("\n=== BUILDING BMI CALCUALTIONS... ===\n") 
# -------------------------------
# HEIGHT: extract + convert to cm
# -------------------------------


def _extract_numeric(x):
    """Extract numeric value from raw height string, handling feet'inches format."""
    try:
        if pd.isna(x):
            return np.nan
        s = str(x).strip()
        # Handle feet'inches format e.g. 5'10 or 5' 10
        m = re.match(r"^\s*(\d+)'\s*(\d+)", s)
        if m:
            return float(int(m.group(1)) * 12 + int(m.group(2)))
        # Otherwise extract first number
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group()) if m else np.nan
    except Exception:
        return np.nan


def _to_cm_by_value(value):
    """Infer unit from value magnitude and convert to cm.
    
    4–7    → bare feet (e.g. 5, 6, 5.5)     → multiply by 30.48
    8–100  → inches (normal adult range)     → multiply by 2.54
    101–130→ ambiguous dead zone             → set NaN
    131–220→ already cm                      → keep as-is
    else   → invalid                         → set NaN
    """
    if pd.isna(value):
        return np.nan
    value = float(value)
    if value < 4:
        return np.nan
    elif value <= 7:
        return value * 30.48   # bare feet
    elif value <= 100:
        return value * 2.54    # inches
    elif value <= 130:
        return np.nan           # ambiguous — let imputation handle
    elif value <= 220:
        return value            # already cm
    else:
        return np.nan


df["HEIGHT_raw_cm"] = df["HEIGHT_raw"].map(_extract_numeric).map(_to_cm_by_value)
df["HEIGHT_raw_cm"] = pd.to_numeric(df["HEIGHT_raw_cm"], errors="coerce")

from config.outliers import lower_bounds, upper_bounds

low_h  = lower_bounds["HEIGHT_raw_cm"]
high_h = upper_bounds["HEIGHT_raw_cm"]
df.loc[(df["HEIGHT_raw_cm"] < low_h) | (df["HEIGHT_raw_cm"] > high_h), "HEIGHT_raw_cm"] = np.nan
print(f"✔ HEIGHT column cleaned, values outside [{low_h}, {high_h}] set to NaN")

low_w  = lower_bounds["WEIGHT"]
high_w = upper_bounds["WEIGHT"]
df.loc[(df["WEIGHT"] < low_w) | (df["WEIGHT"] > high_w), "WEIGHT"] = np.nan
print(f"✔ WEIGHT column cleaned, values outside [{low_w}, {high_w}] set to NaN")

# Fill missing weights from same patient's mean
df["WEIGHT"] = pd.to_numeric(df["WEIGHT"], errors="coerce")
df["WEIGHT"] = df.groupby("SUBJECT_ID")["WEIGHT"].transform(lambda x: x.fillna(x.mean()))
print("✔ Missing weights imputed from patient mean where possible")



# -----------------------------------------------------------
# HEIGHT IMPUTATION 
# -----------------------------------------------------------
# np.random.seed(42)   # to ensure reproducibility of height imputation

from config.imputation import (
    HEIGHT_IMPUTE_MIN, HEIGHT_IMPUTE_MAX,
    HEIGHT_FALLBACK, HEIGHT_IMPUTE_SEED,
)
def impute_height_cm(df, clip_min, clip_max, fallback, seed=None):
    rng = np.random.default_rng(seed)

    df["HEIGHT_raw_cm"] = pd.to_numeric(df["HEIGHT_raw_cm"], errors="coerce")
    df["HEIGHT"] = df["HEIGHT_raw_cm"]

    # Check for inconsistent heights per patient
    inconsistent = df.groupby("SUBJECT_ID")["HEIGHT"].nunique(dropna=True)
    n_inconsistent = (inconsistent > 1).sum()
    if n_inconsistent > 0:
        print(f"  ⚠️ {n_inconsistent} patients have inconsistent heights — collapsing to median")
    else:
        print("  ✓ No inconsistent heights across patients")

    # Collapse to median per patient
    subject_median = df.groupby("SUBJECT_ID")["HEIGHT"].median().rename("_h_median")
    df = df.merge(subject_median, on="SUBJECT_ID", how="left")
    df["HEIGHT"] = df["HEIGHT"].fillna(df["_h_median"])
    df = df.drop(columns=["_h_median"])
    
    # Gender-specific Gaussian imputation for remaining NaNs
    female_vals = df.loc[df["GENDER"] == "F", "HEIGHT"].dropna()
    male_vals   = df.loc[df["GENDER"] == "M", "HEIGHT"].dropna()

    f_mean = female_vals.mean() if len(female_vals) > 0 else fallback["F"]["mean"]
    f_std  = female_vals.std()  if len(female_vals) > 0 else fallback["F"]["std"]
    m_mean = male_vals.mean()   if len(male_vals) > 0   else fallback["M"]["mean"]
    m_std  = male_vals.std()    if len(male_vals) > 0   else fallback["M"]["std"]

    print(f"  Female height: mean={f_mean:.1f}cm, sd={f_std:.1f}cm")
    print(f"  Male height:   mean={m_mean:.1f}cm, sd={m_std:.1f}cm")
    print(f"  Imputed heights clipped to [{clip_min}, {clip_max}] cm")

    mask_f = (df["GENDER"] == "F") & df["HEIGHT"].isna()
    mask_m = (df["GENDER"] == "M") & df["HEIGHT"].isna()

    if mask_f.sum() > 0:
        df.loc[mask_f, "HEIGHT"] = np.clip(
            rng.normal(f_mean, f_std, mask_f.sum()),
            clip_min, clip_max
        )
    if mask_m.sum() > 0:
        df.loc[mask_m, "HEIGHT"] = np.clip(
            rng.normal(m_mean, m_std, mask_m.sum()),
            clip_min, clip_max
        )

     
    subject_final = df.groupby("SUBJECT_ID")["HEIGHT"].median().rename("_h_final")
    df = df.merge(subject_final, on="SUBJECT_ID", how="left")
    df["HEIGHT"] = df["HEIGHT"].fillna(df["_h_final"])
    df = df.drop(columns=["_h_final"])

    return df


df = impute_height_cm(
    df,
    clip_min=HEIGHT_IMPUTE_MIN,
    clip_max=HEIGHT_IMPUTE_MAX,
    fallback=HEIGHT_FALLBACK,
    seed=HEIGHT_IMPUTE_SEED,
)
df["HEIGHT"] = df["HEIGHT"].round().astype("Int64")
print("✔ HEIGHT imputed")

# -----------------------------------------
# BMI CALCULATION
# -----------------------------------------
# OBS the weight column contains ca 130 instances between 200 and 300 kg which seem unrealistically high.   
# They are registered as kg and there is no documentation to decide these are not realistic. 
# If they are registration errors of lbs that have been wrongly registered as kg would this would imply 
#  moving  136 entries from the category "obese" to "high". Still, the total % obesity in the population 
# is approximately as expected (36%) and the potential error seems negligable.  

# -----------------------------------------
# BMI_calc_real — from raw height and weight only
# -----------------------------------------
#calculates numbers when both height and weight was present in raw data 
height_m_real = df["HEIGHT_raw_cm"].astype(float) / 100.0
valid_real = (df["WEIGHT"] > 0) & (height_m_real > 0)

df["BMI_calc_real"] = np.nan
df.loc[valid_real, "BMI_calc_real"] = df.loc[valid_real, "WEIGHT"] / (height_m_real[valid_real] ** 2)
df["BMI_calc_real"] = df["BMI_calc_real"].round(2)
print("✔ BMI_calc_real calculated from raw height and weight")


# -----------------------------------------
# BMI_calc_imputed — from imputed height and weight
# -----------------------------------------

height_m = df["HEIGHT"].astype(float) / 100.0
valid    = (df["WEIGHT"] > 0) & (height_m > 0)
df["BMI_calc"] = np.nan
df.loc[valid, "BMI_calc"] = df.loc[valid, "WEIGHT"] / (height_m[valid] ** 2)
df["BMI_calc"] = df["BMI_calc"].round(2)
print("✔ BMI calculated from height and weight")


#=======================================
#           CLEANING 
#=======================================
print("\n=== REMOVING OUTLIERS... ===\n") 

# -------------------------------
# OUTLIER CLEANING (adults only)
# -------------------------------

def clean_outliers(df):
    """HEIGHT and WEIGHT have actually been cleaned separaetly above, 
    but this function is kept for potential future use if we want to
      clean more variables with the same approach. It also provides a 
      summary of how many values were cleaned per column."""
    total_cleaned = 0
    for col in df.columns:
        before = df[col].notna().sum()
        if col in lower_bounds:
            df[col] = df[col].where(df[col] >= lower_bounds[col])
        if col in upper_bounds:
            df[col] = df[col].where(df[col] <= upper_bounds[col])
        after = df[col].notna().sum()
        cleaned = before - after
        if cleaned > 0:
            print(f"   {col}: {cleaned} values removed")
        total_cleaned += cleaned
    return df, total_cleaned

df, total_cleaned = clean_outliers(df)
print(f"✔ Outliers cleaned — {total_cleaned} total values nulled across all columns")

print("\n=== BUILDING CATEGORICAL FEATURES FOR NUMERICALS WITH HIGH MISSINGNESS... ===\n") 

# -----------------------------------------
# MISSINGNESS OVERVIEW
# -----------------------------------------
vars_to_check = [
    "Creatinine", "BLOOD_UREA_NITRO", "GLUCOSE_BLOOD",
    "SYSTOLIC", "DIASTOLIC", "HEARTRATE",
    "SODIUM", "LOS", "POTASSIUM", "SPO2", "RESP",
    "CHOLESTEROL", "NT-proBNP", "ALBUMIN", "HEMOGLOBIN", "BMI_calc"
]

missing = pd.DataFrame({
    "missing_count":   df[vars_to_check].isna().sum(),
    "missing_percent": df[vars_to_check].isna().mean() * 100
})
print("=== Missing numerical values overview — adult population ===")
print(missing)


#=======================================================
# Step 4c MAKE CATEGORIES OF NUMERICAL VALUES WITH HIGH MISINGNESS  
#=======================================================

# Some of the numeric features has so many missing values that they were made 
# categorical instead of imputed. This makes the missingness  explicit 
# and allows models to learn from it.

# -------------------------------
#   BMI CATEGORY  
#  -------------------------------

from config.groupings.bmi import (
    classify_adult_bmi,
    classify_adult_bmi_codes_only,
    classify_adult_bmi_numbers_only,
    extract_bmi_icd,
    BMI_DTYPE
)

# Main classification: ICD-9 codes first, BMI_calc as fallback
df["BMI_cat"] = df.apply(
    lambda row: classify_adult_bmi(
        row["BMI_calc_real"],
        row["ICD9_CODES"],
        row["BMI_calc"],
    ),
    axis=1
).astype(BMI_DTYPE)
print("✔ BMI_cat created — ICD-9 codes first, BMI_calc as fallback.")

df.drop(columns=["BMI_calc_real"], inplace=True)

# --- QA columns (delete after inspection) ---
df["BMI_icd_code"]    = df["ICD9_CODES"].apply(extract_bmi_icd)
df["QA_BMI_categorization_from_codes_only"]  = df["ICD9_CODES"].apply(classify_adult_bmi_codes_only)
df["QA_BMI_categorization_from_numbers_only"] = df["BMI_calc"].apply(classify_adult_bmi_numbers_only)


# -------------------------------
# Categorize NT-proBNP, ALBUMIN, HEMOGLOBIN and CHOLESTEROL into clinically meaningful bins 
# -------------------------------

from config.groupings.categories import (
    categorize_ntprobnp,
    categorize_cholesterol,
    categorize_albumin,
    # categorize_hemoglobin
)

df["NT-proBNP_cat"] = categorize_ntprobnp(df["NT-proBNP"])
df["CHOLESTEROL_cat"] = categorize_cholesterol(df["CHOLESTEROL"])
df["ALBUMIN_cat"] = categorize_albumin(df["ALBUMIN"])


print("✔ Lab/vital categories created for values of  missingness > 50%")

# -------------------------------------------------------
#          INSERT "MISSING" as a category in categorical features 
# -------------------------------------------------------

#Making MISSING values into a category for these cat. features 
cat_features = [
    "NT-proBNP_cat",
    "CHOLESTEROL_cat",
    "ALBUMIN_cat",
    "BMI_cat"
    ]

for col in cat_features:
    df[col] = df[col].astype("category")  # ensure categorical
    if "Missing" not in df[col].cat.categories:
        df[col] = df[col].cat.add_categories(["Missing"])
    df[col] = df[col].fillna("Missing")

print("✔ Added 'MISSING' as a separate category in categorical features: {}.".format(cat_features))


# ============================================================
#    FORMATTING
# ============================================================  

# -------------------------------------------------------
#      ORDINAL ENCODING FOR CLINICALLY ORDERED CATEGORIES
# -------------------------------------------------------

from config.groupings.categories import (
    apply_measurement_categories,
    apply_ordinal_categories
)

# 1. Apply measurement-based binning
df = apply_measurement_categories(df)

# 2. Apply ordinal encoding to clinically meaningful categories
df = apply_ordinal_categories(df)

print("✔ Ordinal encoding applied to clinically ordered categories.")

# -------------------------------
#   FIX COLUMN ORDER FOR MAXI FILE 
# -------------------------------

# Define desired column order
ordered_columns = [
    # IDs
    "SUBJECT_ID", "ICUSTAY_ID", "HADM_ID",

    # Endpoints
    "READMISSION",  "EXPIRE_FLAG", "HOSPITAL_EXPIRE_FLAG", "HAS_CHARTEVENTS_DATA", "ICUSTAY_EXPIRE", "PRIOR_ICU",
    
    # Demographic info
    "GENDER", "INSURANCE", "LANGUAGE", "LANGUAGE_GROUP", "RELIGION", "RELIGION_GROUP", "MARITAL_STATUS", "MARITAL_GROUP",
    "ETHNICITY","ETHNICITY_GROUP", "IS_NEWBORN", "AGE", "LOS", 
    "initial_DIAGNOSIS", 'ICD9_CODES', 'ICD9_primary', 'ICD9_primary_title', 'ICD9_parent',
    
    # Values
    "HEARTRATE","HEARTRATE_UNIT", 
    "SYSTOLIC", "SYSTOLIC_UNIT","DIASTOLIC","DIASTOLIC_UNIT", 
    "CHOLESTEROL",'CHOLESTEROL_cat', "CHOL","CHOLESTEROL_UNIT",
    "Creatinine", "Creatinine_UNIT", 
    "NT-proBNP",'NT-proBNP_cat',"NT", "NT-proBNP_UNIT",
    "POTASSIUM", "POTASSIUM_UNIT", 
    "BLOOD_UREA_NITRO","BLOOD_UREA_NITRO_UNIT",'SODIUM', 'SODIUM_UNIT', 
    "SPO2", "SPO2_UNIT",
    "RESP", "RESP_UNIT",
    "HEIGHT_raw", "HEIGHT_raw_UNIT", "HEIGHT_raw_cm","HEIGHT",   
    "WEIGHT", "WEIGHT_UNIT", 
    "BMI_calc","BMI_cat","BMI","BMI_icd_code","QA_BMI_categorization_from_codes_only","QA_BMI_categorization_from_numbers_only",

    'GLUCOSE_BLOOD','GLUCOSE_BLOOD_UNIT', 
    'HEMOGLOBIN', 'HEMOGLOBIN_UNIT', 
    'ALBUMIN','ALBUMIN_cat',"ALB", 'ALBUMIN_UNIT', 
      
   
    # Other
    "ADMISSION_TYPE", "ADMISSION_LOCATION", "DISCHARGE_LOCATION", "DBSOURCE",
    "FIRST_CAREUNIT", "LAST_CAREUNIT", "FIRST_WARDID", "LAST_WARDID",
    "INTIME_ICU", "OUTTIME_ICU", "ADMITTIME_HADM", "DISCHTIME_HADM", "DEATHTIME",
    "EDREGTIME", "EDOUTTIME", "DOB", "DOD", "DOD_HOSP", "DOD_SSN", 
    'HEMOGLOBIN_TIME', 'ALBUMIN_TIME', 'CHOLESTEROL_TIME', 'Creatinine_TIME', 
    'GLUCOSE_BLOOD_TIME', 'NT-proBNP_TIME', 'POTASSIUM_TIME', 'SODIUM_TIME', 'BLOOD_UREA_NITRO_TIME', 'SBP_TIME', 'DBP_TIME'
]

#Drop certain columns if they exist (artifact from merging)
df = df.drop(columns=["ROW_ID"], errors="ignore")

# Reorder DataFrame: keep known columns in order, then append any extras
extra_columns = [col for col in df.columns if col not in ordered_columns]
final_columns = ordered_columns + extra_columns

df = df[final_columns]
print("✔ Columns reordered for maxi QA-file and grouped into IDs, endpoints, demographics, values and other info.")

# -------------------------------
#   SAVING MAXI FILE FOR QA AND FUTURE USE
# -------------------------------

# Save maxi version (all columns after cleaning)
df.to_csv(output_file_maxi, index=False)
print(f"\n✅ Dataset saved as: {output_file_maxi}")


# -------------------------------
#   QA CHECKS 
# -------------------------------
print("Unique ICUSTAY_IDs:", df["ICUSTAY_ID"].nunique())
print("\nMaxi dataset shape:", df.shape)



# ============================================================
#   BUILD MINI DATASET FOR MODELING (adults only, non-imputed values)
# ============================================================

print("\n=== BUILDING MINI DATASET FOR MODELING (adults only, non-imputed values) ===\n")


# -------------------------------
#   FEATURE DEFINITIONS (imported from config/features.py)
# -------------------------------
from config.features import (
    ID_COLS,
    CATEGORICAL_COLS,
    FLOAT64_COLS,
    SOCIAL_COLS,
    FEATURES_TO_USE,
    RENAME_DICT,
    GENDER_MAP,
    INT8_COLS,
    INT64_COLS,
    IGNORE_COLS
)

 
# -------------------------------
#   DERIVED COLUMN GROUPS
# -------------------------------
columns_to_keep = list(RENAME_DICT.keys())


# -------------------------------
#   BUILD MINI DATASET OF NON_IMPUTED VALUES 
# -------------------------------
df_mini = df[columns_to_keep].rename(columns=RENAME_DICT)
print("Mini dataset shape:", df_mini.shape)
print("\nMini dataset columns:", df_mini.columns.tolist())

# -------------------------------
#   VALIDATE COLUMNS
# -------------------------------
missing_cols = [c for c in columns_to_keep if c not in df.columns]
if missing_cols:
    print("\n⚠️ WARNING: These columns were NOT found in the MAXI dataset:")
    print(missing_cols)
else:
    print("\nAll MINI columns found in MAXI dataset.")


# -------------------------------
#   ENFORCE SCHEMA
# -------------------------------
def enforce_schema(df):
    df = df.drop(columns=[c for c in IGNORE_COLS if c in df.columns], errors="ignore")
 
    df["gender"] = df["gender"].astype(str).str.strip().map(GENDER_MAP)
 
    for col in INT8_COLS:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").round().astype("Int8")
 
    for col in INT64_COLS:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").round().astype("Int64")
 
    for col in ID_COLS:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
 
    for col in FLOAT64_COLS:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Float64")
 
    for col in CATEGORICAL_COLS + SOCIAL_COLS:
        if col in df:
            df[col] = df[col].astype("category")
    
   
 
    for col in df.columns:
        if df[col].isna().all():
            print(f"⚠ Column {col} is entirely NaN after conversion")
 
    df = df[[c for c in FEATURES_TO_USE if c in df.columns]]
    return df
 
 
df_mini = enforce_schema(df_mini)

# -------------------------------
#   SAVE POPULATION FILE (complete cases only)
# -------------------------------

print("\n=== REMOVING MISSING VALUES AND SAVING POPULATION FILE ===\n")
n_before = len(df_mini)
# df_population = df_mini.dropna(subset=FEATURES_TO_USE)
df_population = remove_missing_rows(df_mini, FEATURES_TO_USE)
n_after = len(df_population)

print(f"\nRows before removing missing values: {n_before}")
print(f"Rows after:                           {n_after}")
print(f"Rows removed:                         {n_before - n_after}")


df_population.to_csv(output_file, index=False)
print(f"\n✅ Population file saved to: {output_file}")

# ============================================================
#   FINAL QA CHECKS
# ============================================================
print("\n=== FINAL QA CHECKS ===\n")

# --- Population flow ---
print("--- Population ---")
print(f"  Total admissions:               {len(df_population)}")
print(f"  Total unique patients:          {df_population['subject_id'].nunique()}")
print(f"  Rows lost to removal due to missingness:   {n_before - n_after}")

# --- Endpoint sanity ---
print("\n--- Readmission (target variable) ---")
print(f"  Readmission rate:               {df_population['readmission'].mean():.1%}")
print(df_population['readmission'].value_counts().to_string())

# --- Newborn sanity (should be 0 after removal) ---
num_flagged_newborns = df_population.loc[df_population["age"] == 0, "subject_id"].nunique()
print(f"\n--- Newborn check ---")
print(f"  Patients with age == 0:         {num_flagged_newborns}")
if num_flagged_newborns > 0:
    print("  ⚠️  WARNING: Newborns detected in final population — check pipeline")
else:
    print("  ✓ No newborns in final population")

# --- Missingness check ---
print("\n--- Missingness in final population ---")
remaining_missing = df_population[FEATURES_TO_USE].isna().sum()
remaining_missing = remaining_missing[remaining_missing > 0]
if len(remaining_missing) > 0:
    print("  ⚠️  Unexpected missing values found:")
    print(remaining_missing.to_string())
else:
    print("  ✓ No missing values in final population")

# --- BMI distribution ---
print("\n--- BMI category distribution ---")
print(df_population["bmi"].value_counts(dropna=False).to_string())

# --- Demographics ---
print("\n--- Demographics ---")
print(f"  Age:    mean={df_population['age'].mean():.1f},  min={df_population['age'].min()},  max={df_population['age'].max()}")
print(f"  Gender: {df_population['gender'].value_counts().to_dict()}")

# --- Schema ---
print("\n--- Dtypes ---")
print(df_population.dtypes.to_string())

print("\n=== QA COMPLETE ===")