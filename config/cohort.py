# config/cohort.py
# -------------------------------------------------------
# All cohort inclusion/exclusion and flag decisions
# -------------------------------------------------------
import pandas as pd

COHORT = {
    "include_newborns":      False,  # keep NICU/age-0 patients in the cohort
    "remove_icu_expired":    True,   # drop stays where the patient died in-ICU
    "remove_missing_rows":   True,   # drop incomplete cases (dropna on FEATURES_TO_USE)
    "remove_organ_donors":   True,   # these must be dropped to get the correct readmission calculation, as they are not really readmissions but planned returns for organ donation
}

def remove_icu_expired(df, cfg=COHORT):
    if not cfg["remove_icu_expired"]:
        print("✔ ICU-expired stays retained (remove_icu_expired=False).")
        return df
    expire = pd.to_numeric(df["ICUSTAY_EXPIRE"], errors="coerce").fillna(0).astype(int)
    n = int((expire == 1).sum())
    df = df.loc[expire != 1].copy()
    print(f"✔ ICU-expired stays removed. Remaining rows: {len(df)}")
    return df

def remove_newborns(df, cfg=COHORT):
    if cfg["include_newborns"]:
        print("✔ Newborns retained (include_newborns=True).")
        return df
    if "IS_NEWBORN" not in df.columns:
        print("⚠️ IS_NEWBORN column not found — skipping newborn removal")
        return df
    n = int((df["IS_NEWBORN"] == 1).sum())
    df = df[df["IS_NEWBORN"] == 0].copy()
    print(f"✔ Removed {n} newborns. Remaining rows: {len(df)}")
    return df

def remove_missing_rows(df, features, cfg=COHORT):
    if not cfg["remove_missing_rows"]:
        return df.copy()
    return df.dropna(subset=features)
