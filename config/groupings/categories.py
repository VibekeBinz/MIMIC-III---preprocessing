# cleaning/groupings/categories.py

import pandas as pd
import numpy as np
from pandas.api.types import CategoricalDtype


def _to_numeric(series):
    """Safely convert a series to numeric, coercing errors to NaN."""
    return pd.to_numeric(series, errors="coerce")

# ======================================================
#  Measurement-based categories 
# ======================================================
# NT-proBNP
NT_BINS = [-np.inf, 1000, 3000, np.inf]
NT_LABELS = ["Normal", "Acute", "Critical"]
NT_DTYPE = pd.CategoricalDtype(categories=NT_LABELS, ordered=True)

def categorize_ntprobnp(series):
    series = _to_numeric(series)
    cat = pd.cut(series, bins=NT_BINS, labels=NT_LABELS)  
    return cat 

# CHOLESTEROL
CHOL_BINS = [-np.inf, 200, 300, np.inf]
CHOL_LABELS = ["Lowrisk", "Intermediate", "Highrisk"]
CHOL_DTYPE = pd.CategoricalDtype(categories=CHOL_LABELS, ordered=True)

def categorize_cholesterol(series):
    series = _to_numeric(series)
    cat = pd.cut(series, bins=CHOL_BINS, labels=CHOL_LABELS)
    return cat


# ALBUMIN
ALB_BINS = [-np.inf, 3.5, 5.0, np.inf]
ALB_LABELS = ["Low", "Normal", "High"]
ALB_DTYPE = pd.CategoricalDtype(categories=ALB_LABELS, ordered=True)

def categorize_albumin(series):
    series = _to_numeric(series)
    cat = pd.cut(series, bins=ALB_BINS, labels=ALB_LABELS)
    return cat




# ======================================================
#  Ordinal encoding for clinically meaningful categories
# ======================================================

ORDINAL_CATEGORY_MAPS = {


    # BMI categories 
    "BMI_cat":("BMI", [
        "Underweight",
        "Normal",
        "High",
        "Obese",
        "Morbidly obese"
    ]),

    "ALBUMIN_cat": ("ALB",[
        "Low",
        "Normal",
        "High"
    ]),

    "CHOLESTEROL_cat": ("CHOL", [
        "Lowrisk", 
        "Intermediate", 
        "Highrisk"
    ]),

     "NT-proBNP_cat": ("NT", [
        "Normal",
        "Acute",
        "Critical"
    ])

}

def apply_ordinal_categories(df):
    """
    Create new ordinal integer columns from clinically meaningful categories.
    Original categorical columns are preserved.
    """
    for col, (new_col, order) in ORDINAL_CATEGORY_MAPS.items():
        if col in df.columns:
            dtype = CategoricalDtype(categories=order, ordered=True)
            df[new_col] = df[col].astype(dtype).cat.codes.astype("Int64")

    return df





# ======================================================
#  Unified entry point
# ======================================================

def apply_measurement_categories(df):
    """Apply measurement-based binning."""
    if "NT-proBNP" in df.columns:
        df["NT-proBNP_cat"] = categorize_ntprobnp(df["NT-proBNP"])

    if "CHOLESTEROL" in df.columns:
        df["CHOLESTEROL_cat"] = categorize_cholesterol(df["CHOLESTEROL"])

    if "ALBUMIN" in df.columns:
        df["ALBUMIN_cat"] = categorize_albumin(df["ALBUMIN"])

    # if "HEMOGLOBIN" in df.columns:
    #     df["HEMOGLOBIN_cat"] = categorize_hemoglobin(df["HEMOGLOBIN"])

    return df
