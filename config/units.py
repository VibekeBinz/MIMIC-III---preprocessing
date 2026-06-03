# -----------------------------------------
# UNIT CONVERSION - REFERENCE DOCUMENTATION 
# -----------------------------------------
weight_item_units = {
    580: "kg",
    581: "kg",
    4183: "kg",
    763: "kg",
    3580: "kg",
    3583: "kg",
    3693: "kg",
    224639: "kg",
    226512: "kg",
    226531: "lbs"
}

height_item_units = {
    1394: "in",
    226707: "in",
    226730: "cm"
}


#----------------------------------
#     HEIGHT CONVERSION
#----------------------------------

def convert_height_to_cm(value, unit):
    if value is None:
        return None
    if unit == "cm":
        return value
    if unit == "in":
        return value * 2.54
    if unit == "m":
        return value * 100
    return None
