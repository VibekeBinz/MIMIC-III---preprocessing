# cleaning/groupings/demo.py

import pandas as pd


# -----------------------------------------
# ETHNICITY MAPPING
# -----------------------------------------

ETHNICITY_MAP = {
    'WHITE': 'WHITE',
    'WHITE - RUSSIAN': 'WHITE',
    'WHITE - OTHER EUROPEAN': 'WHITE',
    'PORTUGUESE': 'WHITE',
    'WHITE - BRAZILIAN': 'WHITE',
    'WHITE - EASTERN EUROPEAN': 'WHITE',

    'BLACK/AFRICAN AMERICAN': 'BLACK',
    'BLACK/CAPE VERDEAN': 'BLACK',
    'BLACK/HAITIAN': 'BLACK',
    'BLACK/AFRICAN': 'BLACK',

    'UNKNOWN/NOT SPECIFIED': 'MISSING',
    'PATIENT DECLINED TO ANSWER': 'MISSING',
    'UNABLE TO OBTAIN': 'MISSING',

    'HISPANIC OR LATINO': 'HISPANIC',
    'HISPANIC/LATINO - PUERTO RICAN': 'HISPANIC',
    'HISPANIC/LATINO - DOMINICAN': 'HISPANIC',
    'HISPANIC/LATINO - GUATEMALAN': 'HISPANIC',
    'HISPANIC/LATINO - CUBAN': 'HISPANIC',
    'HISPANIC/LATINO - SALVADORAN': 'HISPANIC',
    'HISPANIC/LATINO - MEXICAN': 'HISPANIC',
    'HISPANIC/LATINO - CENTRAL AMERICAN (OTHER)': 'HISPANIC',
    'HISPANIC/LATINO - COLOMBIAN': 'HISPANIC',
    'SOUTH AMERICAN': 'HISPANIC',
    'HISPANIC/LATINO - HONDURAN': 'HISPANIC',

    'OTHER': 'OTHER',
    'MULTI RACE ETHNICITY': 'OTHER',
    'AMERICAN INDIAN/ALASKA NATIVE': 'OTHER',
    'MIDDLE EASTERN': 'OTHER',
    'NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER': 'OTHER',
    'CARIBBEAN ISLAND': 'OTHER',
    'AMERICAN INDIAN/ALASKA NATIVE FEDERALLY RECOGNIZED TRIBE': 'OTHER',

    'ASIAN': 'ASIAN',
    'ASIAN - CHINESE': 'ASIAN',
    'ASIAN - ASIAN INDIAN': 'ASIAN',
    'ASIAN - VIETNAMESE': 'ASIAN',
    'ASIAN - FILIPINO': 'ASIAN',
    'ASIAN - CAMBODIAN': 'ASIAN',
    'ASIAN - OTHER': 'ASIAN',
    'ASIAN - KOREAN': 'ASIAN',
    'ASIAN - JAPANESE': 'ASIAN',
    'ASIAN - THAI': 'ASIAN',
}


# -----------------------------------------
# MARITAL STATUS MAPPING
# -----------------------------------------

MARITAL_MAP = {
    'MARRIED': 'MARRIED',
    'LIFE PARTNER': 'MARRIED',
    'SINGLE': 'SINGLE',
    'DIVORCED': 'DIVORCED/SEPARATED',
    'SEPARATED': 'DIVORCED/SEPARATED',
    None: 'MISSING',
    'UNKNOWN (DEFAULT)': 'MISSING',
    'WIDOWED': 'WIDOWED',
}


# -----------------------------------------
# RELIGION MAPPING
# -----------------------------------------

RELIGION_MAP = {
    "CATHOLIC": "CHRISTIAN",
    'PROTESTANT QUAKER': 'CHRISTIAN',
    'EPISCOPALIAN': 'CHRISTIAN',
    'CHRISTIAN SCIENTIST': 'CHRISTIAN',
    "JEHOVAH'S WITNESS": 'CHRISTIAN',
    'UNITARIAN-UNIVERSALIST': 'CHRISTIAN',
    '7TH DAY ADVENTIST': 'CHRISTIAN',
    'BAPTIST': 'CHRISTIAN',
    'LUTHERAN': 'CHRISTIAN',
    'METHODIST': 'CHRISTIAN',

    'GREEK ORTHODOX': 'ORTHODOX',
    'ROMANIAN EAST. ORTH': 'ORTHODOX',

    'JEWISH': 'JEWISH/HEBREW',
    'HEBREW': 'JEWISH/HEBREW',

    'NOT SPECIFIED': 'MISSING',
    'UNOBTAINABLE': 'MISSING',
    'OTHER': 'MISSING',
    None: 'MISSING',

    'BUDDHIST': 'BUDDHIST/HINDU',
    'HINDU': 'BUDDHIST/HINDU',

    'MUSLIM': 'MUSLIM',
}


# -----------------------------------------
# LANGUAGE MAPPING
# -----------------------------------------

LANGUAGE_MAP = {
    "ENGL": "ENGL",
    "AMER": "ENGL",

    "SPAN": "HISP",
    "*SPA": "HISP",
    "PORT": "HISP",
    "HAIT": "HISP",

    "MISSING": "MISSING",
    "UNOBTAINABLE": "MISSING",
}


# -----------------------------------------
# APPLY ALL DEMOGRAPHIC GROUPINGS
# -----------------------------------------

def apply_demographic_groupings(df):
    """
    Applies ethnicity, marital status, religion, and language groupings.
    Unmapped values become 'OTHER'.
    Original NaNs become 'MISSING'.
    """

    mapping_specs = [
        ("LANGUAGE", "LANGUAGE_GROUP", LANGUAGE_MAP),
        ("RELIGION", "RELIGION_GROUP", RELIGION_MAP),
        ("MARITAL_STATUS", "MARITAL_GROUP", MARITAL_MAP),
        ("ETHNICITY", "ETHNICITY_GROUP", ETHNICITY_MAP),
    ]

    for source_col, target_col, mapping in mapping_specs:
        if source_col in df.columns:
            df[target_col] = df[source_col].map(mapping)

            # original NaNs → MISSING
            df.loc[df[source_col].isna(), target_col] = "MISSING"

            # unmapped → OTHER
            df[target_col] = df[target_col].fillna("OTHER")

    return df