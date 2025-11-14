class TeaProfileFields:
    ID = "id"

    NAME = "name"
    ALTERNATIVE_NAMES = "alternative_names"
    TEA_TYPE = "tea_type"
    CULTIVARS = "cultivars"
    PROCESSING = "processing"
    OXIDATION_LEVEL = "oxidation_level"
    CULTURAL_SIGNIFICANCE = "cultural_significance"
    CULTURAL_SIGNIFICANCE_SOURCE = "cultural_significance_source"

    COUNTRY_OF_ORIGIN = "country_of_origin"
    SUBREGIONS = "subregions"
    AVG_PRICE_PER_OZ_USD = "avg_price_per_oz_usd"

    LIQUOR_APPEARANCE = "liquor_appearance"
    LIQUOR_AROMA = "liquor_aroma"
    LIQUOR_TASTE = "liquor_taste"
    LIQUOR_BODY_MOUTHFEEL = "liquor_body_mouthfeel"
    BODY_EFFECT = "body_effect"

    DRY_LEAF_APPEARANCE = "dry_leaf_appearance"
    DRY_LEAF_AROMA = "dry_leaf_aroma"

    WET_LEAF_APPEARANCE = "wet_leaf_appearance"
    WET_LEAF_AROMA = "wet_leaf_aroma"

REQUIRED_TEA_PROFILE_FIELDS = [
    TeaProfileFields.ID,
    TeaProfileFields.NAME,
    TeaProfileFields.TEA_TYPE,
    TeaProfileFields.CULTIVARS,
    TeaProfileFields.COUNTRY_OF_ORIGIN,
    TeaProfileFields.LIQUOR_APPEARANCE,
    TeaProfileFields.LIQUOR_AROMA,
    TeaProfileFields.LIQUOR_TASTE,
]