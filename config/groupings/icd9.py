#ICD9 CODES 

#Defines icd9 grouping category based on first 3 digits of code, or V/E code prefix. 
import pandas as pd



def icd9_parent(code):
    if pd.isna(code):
        return "UNKNOWN"

    code = code.strip()

    # V and E codes
    if code.startswith("V"):
        return "Supplementary factors (V-codes)"
    if code.startswith("E"):
        return "External causes (E-codes)"

    try:
        num = int(code[:3])
    except:
        return "UNKNOWN"

    if 1 <= num <= 139:
        return "Infectious diseases"
    elif 140 <= num <= 239:
        return "Neoplasms"
    elif 240 <= num <= 279:
        return "Endocrine/metabolic"
    elif 280 <= num <= 289:
        return "Blood disorders"
    elif 290 <= num <= 319:
        return "Mental disorders"
    elif 320 <= num <= 389:
        return "Nervous system"
    elif 390 <= num <= 459:
        return "Circulatory system"
    elif 460 <= num <= 519:
        return "Respiratory"
    elif 520 <= num <= 579:
        return "Digestive"
    elif 580 <= num <= 629:
        return "Genitourinary"
    elif 630 <= num <= 679:
        return "Pregnancy"
    elif 680 <= num <= 709:
        return "Skin"
    elif 710 <= num <= 739:
        return "Musculoskeletal"
    elif 740 <= num <= 759:
        return "Congenital"
    elif 760 <= num <= 779:
        return "Perinatal"
    elif 780 <= num <= 799:
        return "Symptoms/ill-defined"
    elif 800 <= num <= 999:
        return "Injury/poisoning"
    else:
        return "UNKNOWN"



# Keyword → ICD9_parent mapping

keyword_map = {
    # Infectious
    "sepsis": "Infectious diseases",
    "septic": "Infectious diseases",
    "infection": "Infectious diseases",
    "pneumonia": "Respiratory",

    # Cardiac / circulatory
    "cardiac": "Circulatory system",
    "mi": "Circulatory system",
    "myocardial": "Circulatory system",
    "heart failure": "Circulatory system",
    "chf": "Circulatory system",
    "arrhythmia": "Circulatory system",
    "afib": "Circulatory system",

    # Respiratory
    "respiratory": "Respiratory",
    "copd": "Respiratory",
    "asthma": "Respiratory",
    "hypoxia": "Respiratory",

    # Neurologic
    "stroke": "Nervous system",
    "cva": "Nervous system",
    "seizure": "Nervous system",

    # GI
    "gi bleed": "Digestive",
    "gastrointestinal": "Digestive",
    "pancreatitis": "Digestive",

    # Renal
    "renal": "Genitourinary",
    "kidney": "Genitourinary",
    "aki": "Genitourinary",

    # Trauma
    "trauma": "Injury/poisoning",
    "fracture": "Injury/poisoning",
}



def infer_parent_from_initial(dx):
    if pd.isna(dx):
        return "UNKNOWN"
    text = dx.lower()
    for keyword, parent in keyword_map.items():
        if keyword in text:
            return parent
    return "UNKNOWN"