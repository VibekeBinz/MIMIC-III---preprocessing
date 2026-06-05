# config/item_ids.py
# MIMIC-III CHARTEVENTS ITEMIDs
# The ITEM IDs selected for vitals and lab measurments. 
# Selected based on keyword search, manually verified for unit consistency and value ranges.

# CHARTEVENTS - VITALS 
heart_rate_ids = [211, 220045]
resp_rate_ids = [618, 615, 220210, 224690]
spo2_ids = [646, 220277, 5636, 3288] # 646 is pulse oximetry, 220277 is spo2 from metavision, 5636 is spo2 from carevue, 3288 is O2 sat pre proceudre which is closest to first measurement for some patients, only used to fiull in missing data gaps.
height_ids = [226707, 226730, 1394]
weight_ids = [226512, 224639, 580, 581, 763]  # 226531 is lbs, converted to kg in Step1a
weight_lbs_ids = [226531]  # for unit conversion in Step1a

paired_bp_pairs = [
    (51, 8368),           # Arterial BP — invasive (carevue)
    (442, 8440),          # Manual BP — invasive (carevue)
    (6701, 8555),         # Arterial BP #2 — invasive (carevue)
    (220050, 220051),     # Arterial Blood Pressure — invasive (metavision)
    (225309, 225310),     # ART BP — invasive (metavision)
    (220179, 220180),     # Non-Invasive BP (metavision)
    (455, 8441),          # NBP cuff (carevue)
]
extra_sbp_ids = [3323]
extra_dbp_ids = [8364]

# LAB EVENTS - LABS 
creatinine_ids = [50912]
bun_ids = [51006]
potassium_ids = [50971, 50822] #50971 is blood serum, fill in  50822 blood gas where missing.
sodium_ids = [50983, 50824] #50983 chemistry preferred, fill in 50824 blood gas if missing 
glucose_blood_ids = [50931, 50809] #primary is 50931 chemistry, the other is blood gas so only for filling missing. 
hemoglobin_ids = [51222, 50811] #primary is 51222 Hematology (CBC), 50811 is blood gas so only for filling missing. 
albumin_ids = [50862]
cholesterol_ids = [50907] # total cholesterol only
ntprobnp_ids = [50963]


