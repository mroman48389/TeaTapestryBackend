from sqlalchemy import Column, Integer, String, Numeric, ARRAY, Text

from src.db.base import Base

from src.constants.tea_profiles_constants import TeaProfileFields, REQUIRED_TEA_PROFILE_FIELDS
from src.constants.model_metadata_constants import DELIMITER_INFO_DICT, IS_PRICE_INFO_DICT

def is_nullable(field: str) -> bool:
    return field not in REQUIRED_TEA_PROFILE_FIELDS

class TeaProfile(Base):
    # SQLAlchemy needs this dunder to be called tablename to
    # do its mapping.
    __tablename__ = "tea_profiles"

    id = Column(Integer, primary_key=True)

    # most common English name, ex: Dragon Well
    name = Column(String, 
        nullable=is_nullable(TeaProfileFields.NAME)
    )
    # ex: Dragon Well is Longjing, Lung Ching as well
    alternative_names = Column(ARRAY(String), 
        nullable=is_nullable(TeaProfileFields.ALTERNATIVE_NAMES),
        info=DELIMITER_INFO_DICT
    )
    # green, white, yellow, oolong, black/red, dark (pu-erh), non-camellia
    # sinensis (herbal, rooibos, yerba mate, tulsi, chai, camellia taliensis)
    tea_type = Column(String, 
        nullable=is_nullable(TeaProfileFields.TEA_TYPE)
    )
    # ex: Qunti Zhong, Longjing #43 for Dragon Well
    cultivars = Column(ARRAY(String), 
        nullable=is_nullable(TeaProfileFields.CULTIVARS),
        info=DELIMITER_INFO_DICT
    )
    # pan-fired, steamed, scented/flavored, etc,
    processing = Column(Text, 
        nullable=is_nullable(TeaProfileFields.PROCESSING)
    )
    # ex: Dragonwell is very low (typically 0%)
    oxidation_level = Column(String, 
        nullable=is_nullable(TeaProfileFields.OXIDATION_LEVEL)
    )
    # top 10 famous Chinese tea? geographically protected? story behind name,
    # etc.
    cultural_significance = Column(Text, 
        nullable=is_nullable(TeaProfileFields.CULTURAL_SIGNIFICANCE)
    )
    cultural_significance_source = Column(String, 
        nullable=is_nullable(TeaProfileFields.CULTURAL_SIGNIFICANCE_SOURCE)
    )

    # ex: China
    country_of_origin = Column(String, 
        nullable=is_nullable(TeaProfileFields.COUNTRY_OF_ORIGIN)
    )  
    # As much info as available, such as Hangzhou (city), Zhejiang (province)
    # for Dragon Well
    subregions = Column(ARRAY(String), 
        nullable=is_nullable(TeaProfileFields.SUBREGIONS),
        info=DELIMITER_INFO_DICT
    )
    # not sure how to get this information easily yet
    avg_price_per_oz_usd = Column(Numeric(7, 2), 
        nullable=is_nullable(TeaProfileFields.AVG_PRICE_PER_OZ_USD),
        info=IS_PRICE_INFO_DICT
    )

    liquor_appearance = Column(ARRAY(String), 
        nullable=is_nullable(TeaProfileFields.LIQUOR_APPEARANCE),
        info=DELIMITER_INFO_DICT
    )
    liquor_aroma = Column(ARRAY(String), 
        nullable=is_nullable(TeaProfileFields.LIQUOR_AROMA),
        info=DELIMITER_INFO_DICT
    )
    # includes aftertaste, hui gan, etc,
    liquor_taste = Column(ARRAY(String), 
        nullable=is_nullable(TeaProfileFields.LIQUOR_TASTE),
        info=DELIMITER_INFO_DICT
    )
    # includes astringency, etc,
    liquor_body_mouthfeel = Column(ARRAY(String), 
        nullable=is_nullable(TeaProfileFields.LIQUOR_BODY_MOUTHFEEL),
        info=DELIMITER_INFO_DICT
    ) 
    # calming, mouth-watering, alert, astringent, etc.
    body_effect = Column(ARRAY(String), 
        nullable=is_nullable(TeaProfileFields.BODY_EFFECT),
        info=DELIMITER_INFO_DICT
    )

    # flat, curled, rolled, different color shades, relative leaf size, etc.
    dry_leaf_appearance = Column(ARRAY(String), 
        nullable=is_nullable(TeaProfileFields.DRY_LEAF_APPEARANCE),
        info=DELIMITER_INFO_DICT
    )
    dry_leaf_aroma = Column(ARRAY(String), 
        nullable=is_nullable(TeaProfileFields.DRY_LEAF_AROMA),
        info=DELIMITER_INFO_DICT
    )

    wet_leaf_appearance = Column(ARRAY(String), 
        nullable=is_nullable(TeaProfileFields.WET_LEAF_APPEARANCE),
        info=DELIMITER_INFO_DICT
    )
    wet_leaf_aroma = Column(ARRAY(String), 
        nullable=is_nullable(TeaProfileFields.WET_LEAF_AROMA),
        info=DELIMITER_INFO_DICT
    )

    # SQL:
    #
    # CREATE TABLE tea_profiles (
    #     id SERIAL PRIMARY KEY,
    #
    #     name VARCHAR NOT NULL,
    #     alternative_names TEXT[],
    #     tea_type VARCHAR NOT NULL,
    #     cultivars TEXT[] NOT NULL,
    #     processing TEXT,
    #     oxidation_level VARCHAR,
    #     cultural_significance TEXT,
    #     cultural_significance_source VARCHAR
    #
    #     country_of_origin VARCHAR NOT NULL,
    #     subregions TEXT[],
    #     avg_price_per_oz_usd NUMERIC(7, 2),
    #
    #     liquor_appearance TEXT[] NOT NULL,
    #     liquor_aroma TEXT[] NOT NULL,
    #     liquor_taste TEXT[] NOT NULL,
    #     liquor_body_mouthfeel TEXT[],
    #     body_effect TEXT[],
    #
    #     dry_leaf_appearance TEXT[],
    #     dry_leaf_aroma TEXT[],

    #     wet_leaf_appearance TEXT[],
    #     wet_leaf_aroma TEXT[]
    # );
    #
    #
    # Note that SERIAL is an auto-incrementing INTEGER

