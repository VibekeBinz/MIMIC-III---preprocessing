# config/imputation.py
import pandas as pd


# -------------------------------------------------------
# Parameters for gender-specific height imputation (decisions only)
# -------------------------------------------------------

# Plausible adult-height clip band for SYNTHETIC (imputed) values, in cm.
# Independent of the cleaning outlier bounds so one real short/tall
# measurement can't drag the imputation range.
HEIGHT_IMPUTE_MIN = 150
HEIGHT_IMPUTE_MAX = 190

# Fallback distribution params used only if a gender has no observed heights.
HEIGHT_FALLBACK = {
    "F": {"mean": 163.0, "std": 3.0},
    "M": {"mean": 176.0, "std": 4.0},
}

# Seed for reproducible imputation draws.
HEIGHT_IMPUTE_SEED = 42





# -------------------------------------------------------
# Parameters for AGE imputation for patients above 89. 
# ----------------------------------
# Elderly age synthetic imputation parameters
# Used to de-identify patients >89 per MIMIC protocol.
# Half-Gaussian distribution ensures all sampled ages >= 89,
# with conservative spread to avoid implausible extreme ages.

ELDERLY_AGE_MEAN    = 89
ELDERLY_AGE_SD      = 4
ELDERLY_AGE_MIN     = 90
ELDERLY_AGE_MAX     = 105
ELDERLY_AGE_SEED    = 42

def sample_elderly(n, mean=ELDERLY_AGE_MEAN, sd=ELDERLY_AGE_SD, 
                   min_age=ELDERLY_AGE_MIN, max_age=ELDERLY_AGE_MAX, rng=None):
    """
    Sample synthetic ages for patients >89 using a half-Gaussian distribution.
    Folds the distribution to ensure all values >= mean, then clips to [min_age, max_age].
    """
    import numpy as np
    if rng is None:
        rng = np.random.default_rng()
    ages = rng.normal(loc=mean, scale=sd, size=n)
    ages = np.abs(ages - mean) + mean
    ages = np.clip(ages, min_age, max_age)
    return ages.round().astype(int)