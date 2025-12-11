from sqlalchemy import Column, Integer, String, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.types.sqlite_compatible_array import SQLiteCompatibleArray
from src.constants.tea_profiles_constants import (
    TeaProfileModelFields, REQUIRED_TEA_PROFILE_MODEL_FIELDS
)
from src.constants.model_metadata_constants import (
    DELIMITER_INFO_DICT, IS_PRICE_INFO_DICT
)


def is_nullable(field: str) -> bool:
    return field not in REQUIRED_TEA_PROFILE_MODEL_FIELDS   


# SQLAlchemy blueprint for database table. This schema defines how data is stored in the database.
class TeaProfileModel(Base):
    # SQLAlchemy needs this dunder to be called tablename to do its mapping.
    __tablename__ = "tea_profiles"

    # id = Column(Integer, primary_key = True)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # most common English name, ex: Dragon Well. Tell Postgres it
    # can rely on the name being unique when we use ON CONFLICT to solve
    # conflicts on upserting. When cleaning CSVs in our pipleline, we 
    # try to remove duplicates, but the database constraint is the final
    # safeguar.
    # name = Column(
    #     String, 
    #     nullable = is_nullable(TeaProfileModelFields.NAME),
    #     unique = True
    # )
    name: Mapped[str] = mapped_column(
        String, 
        nullable = is_nullable(TeaProfileModelFields.NAME),
        unique = True
    )

    # ex: Dragon Well is Longjing, Lung Ching as well.
    # alternative_names = Column(
    #     SQLiteCompatibleArray(),
    #     nullable = is_nullable(TeaProfileModelFields.ALTERNATIVE_NAMES),
    #     info = DELIMITER_INFO_DICT
    # )
    alternative_names: Mapped[list[str]] = mapped_column(
        SQLiteCompatibleArray(),
        nullable = is_nullable(TeaProfileModelFields.ALTERNATIVE_NAMES),
        info = DELIMITER_INFO_DICT
    )

    # green, white, yellow, oolong, black/red, dark (pu-erh), non-camellia
    # sinensis (herbal, rooibos, yerba mate, tulsi, chai, camellia taliensis)
    # tea_type = Column(String, nullable=is_nullable(TeaProfileModelFields.TEA_TYPE))
    tea_type: Mapped[str] = mapped_column(String, nullable=is_nullable(TeaProfileModelFields.TEA_TYPE))

    # ex: Qunti Zhong, Longjing #43 for Dragon Well
    # cultivars = Column(
    #     SQLiteCompatibleArray(),
    #     nullable = is_nullable(TeaProfileModelFields.CULTIVARS),
    #     info = DELIMITER_INFO_DICT
    # )
    cultivars: Mapped[list[str]] = mapped_column(
        SQLiteCompatibleArray(),
        nullable = is_nullable(TeaProfileModelFields.CULTIVARS),
        info = DELIMITER_INFO_DICT
    )

    # pan-fired, steamed, scented/flavored, etc,
    # processing = Column(Text, nullable = is_nullable(TeaProfileModelFields.PROCESSING))
    processing: Mapped[str] = mapped_column(Text, nullable = is_nullable(TeaProfileModelFields.PROCESSING))

    # ex: Dragonwell is very low (typically 0%)
    # oxidation_level = Column(String, nullable = is_nullable(TeaProfileModelFields.OXIDATION_LEVEL))
    oxidation_level: Mapped[str] = mapped_column(String, nullable = is_nullable(TeaProfileModelFields.OXIDATION_LEVEL))

    # top 10 famous Chinese tea? geographically protected? story behind name,
    # etc.
    # cultural_significance = Column(
    #     Text, 
    #     nullable = is_nullable(TeaProfileModelFields.CULTURAL_SIGNIFICANCE)
    # )
    cultural_significance: Mapped[str] = mapped_column(
        Text, 
        nullable = is_nullable(TeaProfileModelFields.CULTURAL_SIGNIFICANCE)
    )

    # cultural_significance_source = Column(
    #     String, 
    #     nullable = is_nullable(TeaProfileModelFields.CULTURAL_SIGNIFICANCE_SOURCE)
    # )
    cultural_significance_source: Mapped[str] = mapped_column(
        String, 
        nullable = is_nullable(TeaProfileModelFields.CULTURAL_SIGNIFICANCE_SOURCE)
    )

    # ex: China
    # country_of_origin = Column(
    #     String,
    #     nullable = is_nullable(TeaProfileModelFields.COUNTRY_OF_ORIGIN)
    # )
    country_of_origin: Mapped[str] = mapped_column(
        String,
        nullable = is_nullable(TeaProfileModelFields.COUNTRY_OF_ORIGIN)
    )

    # As much info as available, such as Hangzhou (city), Zhejiang (province)
    # for Dragon Well
    # subregions = Column(
    #     SQLiteCompatibleArray(),
    #     nullable = is_nullable(TeaProfileModelFields.SUBREGIONS),
    #     info = DELIMITER_INFO_DICT
    # )
    subregions: Mapped[list[str]] = mapped_column(
        SQLiteCompatibleArray(),
        nullable = is_nullable(TeaProfileModelFields.SUBREGIONS),
        info = DELIMITER_INFO_DICT
    )
    # not sure how to get this information easily yet
    # avg_price_per_oz_usd = Column(
    #     Numeric(7, 2),
    #     nullable = is_nullable(TeaProfileModelFields.AVG_PRICE_PER_OZ_USD),
    #     info = IS_PRICE_INFO_DICT
    # )
    avg_price_per_oz_usd: Mapped[float] = mapped_column(
        Numeric(7, 2),
        nullable = is_nullable(TeaProfileModelFields.AVG_PRICE_PER_OZ_USD),
        info = IS_PRICE_INFO_DICT
    )
    
    # liquor_appearance = Column(
    #     SQLiteCompatibleArray(),
    #     nullable = is_nullable(TeaProfileModelFields.LIQUOR_APPEARANCE),
    #     info = DELIMITER_INFO_DICT
    # )
    liquor_appearance: Mapped[list[str]] = mapped_column(
        SQLiteCompatibleArray(),
        nullable = is_nullable(TeaProfileModelFields.LIQUOR_APPEARANCE),
        info = DELIMITER_INFO_DICT
    )

    # liquor_aroma = Column(
    #     SQLiteCompatibleArray(),
    #     nullable = is_nullable(TeaProfileModelFields.LIQUOR_AROMA),
    #     info  =DELIMITER_INFO_DICT
    # )
    liquor_aroma: Mapped[list[str]] = mapped_column(
        SQLiteCompatibleArray(),
        nullable = is_nullable(TeaProfileModelFields.LIQUOR_AROMA),
        info  =DELIMITER_INFO_DICT
    )
    # includes aftertaste, hui gan, etc,
    # liquor_taste = Column(
    #     SQLiteCompatibleArray(),
    #     nullable = is_nullable(TeaProfileModelFields.LIQUOR_TASTE),
    #     info = DELIMITER_INFO_DICT
    # )
    liquor_taste: Mapped[list[str]] = mapped_column(
        SQLiteCompatibleArray(),
        nullable = is_nullable(TeaProfileModelFields.LIQUOR_TASTE),
        info = DELIMITER_INFO_DICT
    )

    # includes astringency, etc,
    # liquor_body_mouthfeel = Column(
    #     SQLiteCompatibleArray(),
    #     nullable = is_nullable(TeaProfileModelFields.LIQUOR_BODY_MOUTHFEEL),
    #     info = DELIMITER_INFO_DICT
    # )
    liquor_body_mouthfeel: Mapped[list[str]] = mapped_column(
        SQLiteCompatibleArray(),
        nullable = is_nullable(TeaProfileModelFields.LIQUOR_BODY_MOUTHFEEL),
        info = DELIMITER_INFO_DICT
    )
    # calming, mouth-watering, alert, astringent, etc.
    # body_effect = Column(
    #     SQLiteCompatibleArray(),
    #     nullable = is_nullable(TeaProfileModelFields.BODY_EFFECT),
    #     info = DELIMITER_INFO_DICT
    # )
    body_effect: Mapped[list[str]] = mapped_column(
        SQLiteCompatibleArray(),
        nullable = is_nullable(TeaProfileModelFields.BODY_EFFECT),
        info = DELIMITER_INFO_DICT
    )

    # flat, curled, rolled, different color shades, relative leaf size, etc.
    # dry_leaf_appearance = Column(
    #     SQLiteCompatibleArray(),
    #     nullable = is_nullable(TeaProfileModelFields.DRY_LEAF_APPEARANCE),
    #     info = DELIMITER_INFO_DICT
    # )
    dry_leaf_appearance: Mapped[list[str]] = mapped_column(
        SQLiteCompatibleArray(),
        nullable = is_nullable(TeaProfileModelFields.DRY_LEAF_APPEARANCE),
        info = DELIMITER_INFO_DICT
    )
    # dry_leaf_aroma = Column(
    #     SQLiteCompatibleArray(),
    #     nullable = is_nullable(TeaProfileModelFields.DRY_LEAF_AROMA),
    #     info = DELIMITER_INFO_DICT
    # )
    dry_leaf_aroma: Mapped[list[str]] = mapped_column(
        SQLiteCompatibleArray(),
        nullable = is_nullable(TeaProfileModelFields.DRY_LEAF_AROMA),
        info = DELIMITER_INFO_DICT
    )

    # wet_leaf_appearance = Column(
    #     SQLiteCompatibleArray(),
    #     nullable = is_nullable(TeaProfileModelFields.WET_LEAF_APPEARANCE),
    #     info = DELIMITER_INFO_DICT
    # )
    wet_leaf_appearance: Mapped[list[str]] = mapped_column(
        SQLiteCompatibleArray(),
        nullable = is_nullable(TeaProfileModelFields.WET_LEAF_APPEARANCE),
        info = DELIMITER_INFO_DICT
    )
    # wet_leaf_aroma = Column(
    #     SQLiteCompatibleArray(),
    #     nullable = is_nullable(TeaProfileModelFields.WET_LEAF_AROMA),
    #     info = DELIMITER_INFO_DICT
    # )
    wet_leaf_aroma: Mapped[list[str]] = mapped_column(
        SQLiteCompatibleArray(),
        nullable = is_nullable(TeaProfileModelFields.WET_LEAF_AROMA),
        info = DELIMITER_INFO_DICT
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
