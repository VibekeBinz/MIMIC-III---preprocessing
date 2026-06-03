# ======================================
# MIMIC-III EXTRACT LAB RESULTS FROM LABEVENTS
# Extract first measurements of key lab tests from LABEVENTS
# ======================================

"""
Data source: Johnson, A., Pollard, T., & Mark, R. (2016). MIMIC-III Clinical Database (version 1.4). 
PhysioNet. RRID:SCR_007345. https://doi.org/10.13026/C2XW26
"""

import pandas as pd
import os
from config.outliers import lower_bounds, upper_bounds


# -----------------------------
# Config 
# -----------------------------
data_path = "RAWDATA/"
labevents_file = os.path.join(data_path, "LABEVENTS.csv")
icustays_file = os.path.join(data_path,"ICUSTAYS.csv")

output_dir = "Data"
os.makedirs(output_dir, exist_ok=True)

output_file = os.path.join(output_dir, "Step1b_first_labs.csv")

# -----------------------------
# Load LABEVENTS
# -----------------------------
use_cols = ["SUBJECT_ID", "HADM_ID", "ITEMID", "CHARTTIME", "VALUE", "VALUEUOM"]
labevents = pd.read_csv(labevents_file, usecols=use_cols, low_memory=False)
labevents["CHARTTIME"] = pd.to_datetime(labevents["CHARTTIME"], errors="coerce")
print("✔ Loaded LABEVENTS")

# -----------------------------
# Load ICU stays (ALL columns, including those without lab measurements, )
# -----------------------------
icustays = pd.read_csv(icustays_file, low_memory=False)
icustays["INTIME"] = pd.to_datetime(icustays["INTIME"], errors="coerce")
icustays["OUTTIME"] = pd.to_datetime(icustays["OUTTIME"], errors="coerce")
print("✔ Loaded ICU stays")

# -----------------------------
# Define grouped ITEMIDs per lab concept
# -----------------------------
from config.item_ids import (
    creatinine_ids, bun_ids, potassium_ids, sodium_ids,
    glucose_blood_ids, hemoglobin_ids, albumin_ids,
    cholesterol_ids, ntprobnp_ids
)

lab_item_groups = {
    "Creatinine": creatinine_ids,
    "BLOOD_UREA_NITRO": bun_ids,
    "POTASSIUM": potassium_ids,
    "SODIUM": sodium_ids,
    "GLUCOSE_BLOOD": glucose_blood_ids,
    "HEMOGLOBIN": hemoglobin_ids,
    "ALBUMIN": albumin_ids,
    "CHOLESTEROL": cholesterol_ids,
    "NT-proBNP": ntprobnp_ids
}

lab_ids = [item for group in lab_item_groups.values() for item in group]

# Filter LABEVENTS to selected labs
labevents = labevents[labevents["ITEMID"].isin(lab_ids)]
print("✔ Filtered LABEVENTS to selected lab tests:", list(lab_item_groups.keys()))

# -----------------------------
# Merge LABEVENTS + ICU stays
# -----------------------------
merged = pd.merge(
    labevents,
    icustays[["ICUSTAY_ID", "HADM_ID", "SUBJECT_ID", "INTIME", "OUTTIME"]],
    on=["HADM_ID", "SUBJECT_ID"],
    how="inner"
)


# Keep only labs within ICU stay window
merged = merged[(merged["CHARTTIME"] >= merged["INTIME"]) &
                (merged["CHARTTIME"] <= merged["OUTTIME"])]

print("✔ Filtered labs to ICU stay window")

# -----------------------------
# Assign LABEL to each ITEMID
# -----------------------------
def map_lab_label(itemid):
    for label, ids in lab_item_groups.items():
        if itemid in ids:
            return label
    return None

merged["LABEL"] = merged["ITEMID"].apply(map_lab_label)
print("✔ Mapped ITEMIDs to lab labels")

# -----------------------------
# Apply bounds using helper function
# -----------------------------
merged["VALUE"] = pd.to_numeric(merged["VALUE"], errors="coerce")
merged["VALUEUOM"] = merged["VALUEUOM"].str.lower()

def apply_bounds(df, label):
    """Apply lower/upper bounds to a lab group if defined."""
    if label in lower_bounds:
        df = df[df["VALUE"] >= lower_bounds[label]]
    if label in upper_bounds:
        df = df[df["VALUE"] <= upper_bounds[label]]
    return df

cleaned_groups = []
for label, group in merged.groupby("LABEL"):
    cleaned_groups.append(apply_bounds(group.copy(), label))

merged_clean = pd.concat(cleaned_groups, ignore_index=True)
print("✔ Applied bounds and cleaned lab values")



# -----------------------------
# Pick FIRST valid measurement with PRIORITY FILLING
# -----------------------------

all_results = []

for label, itemids in lab_item_groups.items():

    label_frames = []

    for priority, item in enumerate(itemids):

        subset = merged_clean[merged_clean["ITEMID"] == item].copy()

        if subset.empty:
            continue

        # sort by time
        subset = subset.sort_values(["ICUSTAY_ID", "CHARTTIME"])

        # first valid per ICU stay for this ITEMID
        first = subset.groupby("ICUSTAY_ID").first().reset_index()

        first["priority"] = priority
        first["LABEL"] = label

        label_frames.append(first)

    if not label_frames:
        continue

    label_df = pd.concat(label_frames, ignore_index=True)

    # IMPORTANT:
    # lower priority number = higher importance
    label_df = label_df.sort_values(["ICUSTAY_ID", "priority"])

    # keep best available ITEMID per ICU stay (fills missing progressively)
    label_df = label_df.drop_duplicates(["ICUSTAY_ID"], keep="first")

    all_results.append(label_df)


first_measurements = pd.concat(all_results, ignore_index=True)

print("✔ Extracted PRIORITY-FILLED lab measurements per ICU stay")

# -----------------------------
# Pivot to wide format
# -----------------------------
values = first_measurements.pivot(
    index="ICUSTAY_ID",
    columns="LABEL",
    values="VALUE"
)

units = first_measurements.pivot(
    index="ICUSTAY_ID",
    columns="LABEL",
    values="VALUEUOM"
).add_suffix("_UNIT")

times = first_measurements.pivot(
    index="ICUSTAY_ID",
    columns="LABEL",
    values="CHARTTIME"
).add_suffix("_TIME")

icu_labs_summary = pd.concat([values, units, times], axis=1).reset_index()
print("✔ Pivoted labs to wide format")


# -----------------------------
#  Add ICU identifiers 
# -----------------------------

icu_ids = icustays[["ICUSTAY_ID", "HADM_ID", "SUBJECT_ID"]]

icu_labs_summary = icu_labs_summary.merge(icu_ids, on="ICUSTAY_ID", how="left")
print("✔ Added ICU identifiers")


# -----------------------------
# Save to CSV
# -----------------------------

icu_labs_summary.to_csv(output_file, index=False)

print(f"✅ Saved: {output_file}")

# ---------- PRINT FEATURES (COLUMNS) ----------

print("\n=== Sanity check output_file ===")


# -------------------------------
#    SANITY CHECK 
# -------------------------------
print("Unique ICUSTAY_IDs in LABEVENTS:", icu_labs_summary["ICUSTAY_ID"].nunique())
print("Total rows in LABEVENTS first events:", len(icu_labs_summary))
print("Columns in final dataset:", icu_labs_summary.columns.tolist())


