# ======================================
# MIMIC-III EXTRACT VITALS FROM CHARTEVENTS
# Extract first measurements of key vitals from CHARTEVENTS
# ======================================

"""
Data source: Johnson, A., Pollard, T., & Mark, R. (2016). MIMIC-III Clinical Database (version 1.4). 
PhysioNet. RRID:SCR_007345. https://doi.org/10.13026/C2XW26
"""

import pandas as pd
from tqdm import tqdm
import os
#imports outlier rules and includes for picking values 
from config.outliers import lower_bounds, upper_bounds
import time
start_time = time.time()

# -------------------------------
#       CONFIG 
# -------------------------------

data_path = "RAWDATA/"
chunksize = 1_000_000  # adjust for your RAM
output_dir = "Data"
os.makedirs(output_dir, exist_ok=True)

output_file = os.path.join(output_dir, "Step1a_first_vitals.csv")

# ----------------------------
#    ITEM ID DEFINITIONS  
# ----------------------------


from config.item_ids import (
    heart_rate_ids, resp_rate_ids, spo2_ids,
    height_ids, weight_ids,
    paired_bp_pairs, extra_sbp_ids, extra_dbp_ids
)

# Combined lists for filtering
systolic_bp_ids  = [p[0] for p in paired_bp_pairs] + extra_sbp_ids
diastolic_bp_ids = [p[1] for p in paired_bp_pairs] + extra_dbp_ids


vital_ids = (
    heart_rate_ids + systolic_bp_ids + diastolic_bp_ids + 
    resp_rate_ids + spo2_ids + 
    height_ids + weight_ids
)

# Define relevant rows from CHARTEVENTS
chart_cols = ["ICUSTAY_ID", "ITEMID", "CHARTTIME", "VALUE", "VALUEUOM"] 
chartevents_filtered = []

# -------------------------------
#    LOAD CHARTEVENTS IN CHUNKS
# -------------------------------

print("✔ Loading CHARTEVENTS in chunks...")
for chunk in tqdm(pd.read_csv(
    os.path.join(data_path, "CHARTEVENTS.csv"),
    usecols=chart_cols,
    chunksize=chunksize,
    low_memory=False,
    parse_dates=["CHARTTIME"]   
)):
    chunk = chunk[chunk["ITEMID"].isin(vital_ids)]
    chartevents_filtered.append(chunk)

chartevents = pd.concat(chartevents_filtered, ignore_index=True)
chartevents = chartevents.sort_values(["ICUSTAY_ID", "CHARTTIME"])

print("✔ CHARTEVENTS loaded and sorted")

# --------------------------------------------------------------
#    PROCESS FIRST VALID MEASUREMENTS FROM CHARTEVENTS
# --------------------------------------------------------------

def get_first_valid_measurement(df, itemids, label):
    per_item_results = []
    for priority, item in enumerate(itemids):
        subset = df[df["ITEMID"] == item].copy()
        if subset.empty:
            continue

        # Convert VALUE to numeric
        subset["VALUE"] = pd.to_numeric(subset["VALUE"], errors="coerce")
        subset["VALUEUOM"] = subset["VALUEUOM"].str.lower()

        # -----------------------------------------
        # WEIGHT: convert units to kg, THEN apply bounds
        # -----------------------------------------
        """this itemID is handled different from the others bc it has a different unit. """
        if label == "WEIGHT":
            from config.item_ids import weight_lbs_ids as LBS_ITEMIDS
            # 1) Convert 226531 from lbs -> kg (ignore the unit string, it's wrong)
            is_lbs = subset["ITEMID"].isin(LBS_ITEMIDS)
            subset.loc[is_lbs, "VALUE"] = subset.loc[is_lbs, "VALUE"] * 0.45359237

            # 2) Catch hectogram-coded values in a kg field (non-lbs itemids only)
            big = (~is_lbs) & (subset["VALUE"] > 300)
            subset.loc[big, "VALUE"] = subset.loc[big, "VALUE"] / 10

            # Everything is now in kg
            subset["VALUEUOM"] = "kg"

            # 3) Screen against ONE kg range (applies to all itemids equally)
            subset = subset[subset["VALUE"].between(
                lower_bounds["WEIGHT"], upper_bounds["WEIGHT"]
            )]

        # -----------------------------------------
        # NON-WEIGHT VITALS
        # -----------------------------------------
        else:
            if label in lower_bounds:
                subset = subset[subset["VALUE"] >= lower_bounds[label]]
            if label in upper_bounds:
                subset = subset[subset["VALUE"] <= upper_bounds[label]]

        # Sort by time within this ITEMID
        subset = subset.sort_values(["ICUSTAY_ID", "CHARTTIME"])

        # Take first per ICU stay for THIS ITEMID
        first = subset.groupby("ICUSTAY_ID").first().reset_index()

        # Track priority (lower = better)
        first["priority"] = priority

        per_item_results.append(first)

    # Combine all ITEMIDs
    if not per_item_results:
        return pd.DataFrame(columns=["ICUSTAY_ID", label, f"{label}_UNIT"])

    combined = pd.concat(per_item_results, ignore_index=True)

    # Sort by ICU stay + priority (NOT time anymore)
    combined = combined.sort_values(["ICUSTAY_ID", "priority"])

    # Keep best ITEMID per ICU stay
    combined = combined.drop_duplicates("ICUSTAY_ID", keep="first")

    return combined.rename(columns={
        "VALUE": label,
        "VALUEUOM": f"{label}_UNIT"
    })[["ICUSTAY_ID", label, f"{label}_UNIT"]]


def get_first_paired_bp(df, paired_bp_pairs, extra_sbp_ids, extra_dbp_ids):
    """
    Extract first valid systemic SBP–DBP pair per ICUSTAY_ID.
    Priority order is determined by paired_bp_pairs.
    Extra SBP/DBP are returned separately for imputation.
    """

    # Filter to all BP ITEMIDs
    all_ids = [x for pair in paired_bp_pairs for x in pair] + extra_sbp_ids + extra_dbp_ids
    bp = df[df["ITEMID"].isin(all_ids)].copy()

    bp["VALUE"] = pd.to_numeric(bp["VALUE"], errors="coerce")
    bp["VALUEUOM"] = bp["VALUEUOM"].str.lower()

    # Apply QA bounds
    sbp_low, sbp_high = lower_bounds["SYSTOLIC"], upper_bounds["SYSTOLIC"]
    dbp_low, dbp_high = lower_bounds["DIASTOLIC"], upper_bounds["DIASTOLIC"]

    bp.loc[bp["ITEMID"].isin([p[0] for p in paired_bp_pairs]), "VALUE"] = \
        bp.loc[bp["ITEMID"].isin([p[0] for p in paired_bp_pairs]), "VALUE"].where(
            bp["VALUE"].between(sbp_low, sbp_high)
        )

    bp.loc[bp["ITEMID"].isin([p[1] for p in paired_bp_pairs]), "VALUE"] = \
        bp.loc[bp["ITEMID"].isin([p[1] for p in paired_bp_pairs]), "VALUE"].where(
            bp["VALUE"].between(dbp_low, dbp_high)
        )

    results = []

    # --- PRIORITY LOOP ---
    for sbp_id, dbp_id in paired_bp_pairs:

        sbp = bp[bp["ITEMID"] == sbp_id].copy()
        dbp = bp[bp["ITEMID"] == dbp_id].copy()

        if sbp.empty or dbp.empty:
            continue

        sbp = sbp.sort_values(["ICUSTAY_ID", "CHARTTIME"])
        dbp = dbp.sort_values(["ICUSTAY_ID", "CHARTTIME"])

        sbp_first = sbp.groupby("ICUSTAY_ID").first().reset_index()
        dbp_first = dbp.groupby("ICUSTAY_ID").first().reset_index()

        merged = sbp_first.merge(dbp_first, on="ICUSTAY_ID", suffixes=("_SBP", "_DBP"))

        # Enforce SBP > DBP
        merged = merged[merged["VALUE_SBP"] > merged["VALUE_DBP"]]

        if merged.empty:
            continue

        merged = merged.sort_values("CHARTTIME_SBP").drop_duplicates("ICUSTAY_ID")

        merged["SYSTOLIC"] = merged["VALUE_SBP"]
        merged["DIASTOLIC"] = merged["VALUE_DBP"]
        merged["SYSTOLIC_UNIT"] = merged["VALUEUOM_SBP"]
        merged["DIASTOLIC_UNIT"] = merged["VALUEUOM_DBP"]
        merged["SBP_TIME"] = merged["CHARTTIME_SBP"]
        merged["DBP_TIME"] = merged["CHARTTIME_DBP"]

        results.append(merged[[
            "ICUSTAY_ID",
            "SYSTOLIC", "SYSTOLIC_UNIT", "SBP_TIME",
            "DIASTOLIC", "DIASTOLIC_UNIT", "DBP_TIME"
        ]])

    # If no valid pairs at all
    if not results:
        return pd.DataFrame(columns=[
            "ICUSTAY_ID",
            "SYSTOLIC", "SYSTOLIC_UNIT", "SBP_TIME",
            "DIASTOLIC", "DIASTOLIC_UNIT", "DBP_TIME"
        ])

    # Combine and keep highest priority
    final = pd.concat(results, ignore_index=True)
    final = final.sort_values("ICUSTAY_ID").drop_duplicates("ICUSTAY_ID", keep="first")

    return final


heart_df = get_first_valid_measurement(chartevents, heart_rate_ids, "HEARTRATE")
resp_df = get_first_valid_measurement(chartevents, resp_rate_ids, "RESP")
spo2_df = get_first_valid_measurement(chartevents, spo2_ids, "SPO2")
height_df = get_first_valid_measurement(chartevents, height_ids, "HEIGHT_raw")
weight_df = get_first_valid_measurement(chartevents, weight_ids, "WEIGHT")
bp_df = get_first_paired_bp(
    chartevents,
    paired_bp_pairs,
    extra_sbp_ids,
    extra_dbp_ids
)


print("✔ Extracted first measurements for:",
      
      ["HEARTRATE", "SBP", "DBP", "RESP", "SPO2", "HEIGHT_raw", "WEIGHT"])

# -------------------------------
#   MERGE ALL VITALS
# -------------------------------

vitals = (
    heart_df
    .merge(bp_df, on="ICUSTAY_ID", how="outer")
    .merge(resp_df, on="ICUSTAY_ID", how="outer")
    .merge(spo2_df, on="ICUSTAY_ID", how="outer")
    .merge(height_df, on="ICUSTAY_ID", how="outer")
    .merge(weight_df, on="ICUSTAY_ID", how="outer")
)
print("✔ Merged all vital signs")


# -------------------------------
#    SAVE TO CSV 
# -------------------------------


vitals.to_csv(output_file, index=False)
print("✅ Saved:", output_file)


# -------------------------------
#    SANITY CHECK 
# -------------------------------

# ---------- PRINT FEATURES (COLUMNS) ----------

print("\n=== Features in output_file ===")

print("Unique ICUSTAY_IDs in CHARTEVENTS:", vitals["ICUSTAY_ID"].nunique())
print("Total rows in CHARTEVENTS first events:", len(vitals))
print("Columns in final dataset:", vitals.columns.tolist())

elapsed = (time.time() - start_time) / 60
print(f"\n⏱ Script completed in {elapsed:.1f} minutes")
