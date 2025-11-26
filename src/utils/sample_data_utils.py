from sqlalchemy import String, Numeric, Text, ARRAY

from src.db.models.tea_profiles_model import TeaProfile, TeaProfileFields
from src.db.types.sqlite_compatible_array import SQLiteCompatibleArray

def init_sample_tea_profiles_row(overrides: dict[str, str | list[str]]) -> dict[str, 
    str | list[str] | None]:
    
    row = {}

    for col in TeaProfile.__table__.columns:
        # skip primary key
        if col.name == TeaProfileFields.ID:
            continue  

        # This allows us to pass in a dict with any key-value pairs
        # we want to provide defaults for
        if col.name in overrides:
            row[col.name] = overrides[col.name]

        elif isinstance(col.type, (ARRAY, SQLiteCompatibleArray)):
            row[col.name] = []  

        elif isinstance(col.type, (String, Text)):
            row[col.name] = None

        elif isinstance(col.type, Numeric):
            row[col.name] = None  

        else:
            row[col.name] = None

    return row

def get_sample_tea_profiles_data() -> dict[str, str | list[str] | None]:
    """
        Returns a dict of critical TeaProfile field values for use in tests.
    """

    # name = "Bi Luo Chun"
    # tea_type = "green"
    # cultivars = "Dong Ting; Qing Xin Gan Zai"
    # country_of_origin = "China"
    # liquor_appearance = "slightly hazy; soft, golden, antique yellow"
    # liquor_aroma = "hay; nutty; vegetal; chesnuts"
    # liquor_taste = "hay; vegetal; nutty; pine; spicy; slightly bitter; chestnuts, sweet"
    name = "Bi Luo Chun"
    tea_type = "green"
    cultivars = ["Dong Ting", "Qing Xin Gan Zai"]
    country_of_origin = "China"
    liquor_appearance = ["slightly hazy", "soft, golden, antique yellow"]
    liquor_aroma = ["hay", "nutty", "vegetal", "chesnuts"]
    liquor_taste = [
        "hay", "vegetal", "nutty", "pine", "spicy", "slightly bitter", 
        "chestnuts", "sweet"
    ]

    critical_row_values = {
        TeaProfileFields.NAME: name,
        TeaProfileFields.TEA_TYPE: tea_type,
        TeaProfileFields.CULTIVARS: cultivars,
        TeaProfileFields.COUNTRY_OF_ORIGIN: country_of_origin,
        TeaProfileFields.LIQUOR_APPEARANCE: liquor_appearance,
        TeaProfileFields.LIQUOR_AROMA: liquor_aroma,
        TeaProfileFields.LIQUOR_TASTE: liquor_taste,
    }

    return init_sample_tea_profiles_row(critical_row_values)