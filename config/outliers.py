# cleaning/outliers.py

import pandas as pd




# -----------------------------------------
# DEMOGRAPHICS
# -----------------------------------------

lower_bounds_demo = {
    "AGE": 0,
    "LOS": 0        # cannot be negative
}

upper_bounds_demo = {
    "AGE": 120,
    "LOS": 150     # sanity cap
}
# -----------------------------------------
# PHYSIOLOGICAL RANGES ADULTS 
# -----------------------------------------    
valid_units_vitals = {
    "HEARTRATE": ["bpm", ""],
    "SYSTOLIC": ["mmhg", ""],
    "DIASTOLIC": ["mmhg", ""],
    "RESP": ["/min", "bpm", "breath", "breaths", "insp/min", ""],
    "SPO2": ["%", "bpm", ""],
    "HEIGHT": ["cm", "m", "in", "inch", ""],
    "WEIGHT": ["kg", "lbs", ""]
}
# OBS thee are extreme values, NOT normal clinical ranges  

lower_bounds_adults = {
    "HEARTRATE": 15,            # bpm
    "SYSTOLIC": 30,             # mmhg
    "DIASTOLIC": 10,            # mmhg
    "RESP": 5,                  # bpm (lower than this would likely lead to ventilator support that would artificially bring the measured  number up, therefore assuming too low values are measurement errors)
    "SPO2": 30,                 # %
    "HEIGHT_raw": 1,           # mixed units - inches, meters, other. 40-220
    "HEIGHT_raw_cm": 100,           # cm
    "HEIGHT": 100,               # cm
    "WEIGHT": 20,               # kg
    "BMI_calc": 5,              # kg/m^2
    "GLUCOSE_BLOOD": 5,         # mg/dL
    "POTASSIUM": 1.0,           # meq/L
    "SODIUM": 90,               # meq/L
    "HEMOGLOBIN": 1.5,          # g/dL
    "ALBUMIN": 0.5,             # g/dL
    "Creatinine": 0.1,          # mg/dL
    "BLOOD_UREA_NITRO": 1,      # mg/dL
    "CHOLESTEROL": 20,          # mg/dL
    "NT-proBNP": 0,             # pg/mL
    }

upper_bounds_adults = {
    "HEARTRATE": 260,           # bpm
    "SYSTOLIC": 300,            # mmhg
    "DIASTOLIC": 230,           # mmhg
    "RESP": 100,                # bpm
    "SPO2": 100,                # %
    "HEIGHT_raw": 220,          # mixed units - inches, meters, other.    
    "HEIGHT_raw_cm": 220,           # cm 
    "HEIGHT": 220,              # cm
    "WEIGHT": 300,              # kg
    "BMI_calc": 150,              # kg/m^2
    "GLUCOSE_BLOOD": 2600,      # mg/dL
    "POTASSIUM": 12,            # meq/L
    "SODIUM": 200,              # meq/L
    "HEMOGLOBIN": 30,           # g/dL
    "ALBUMIN": 10,              # g/dL
    "Creatinine": 30,           # mg/dL
    "BLOOD_UREA_NITRO": 400,    # mg/dL
    "CHOLESTEROL": 1000,        # mg/dL
    "NT-proBNP": 100000,        # pg/mL
}



# -----------------------------------------
# COMBINED ACCESS
# -----------------------------------------

lower_bounds = {
    **lower_bounds_adults,
    **lower_bounds_demo
}

upper_bounds = {
    **upper_bounds_adults,
    **upper_bounds_demo
}


valid_units = {
    **valid_units_vitals
}
