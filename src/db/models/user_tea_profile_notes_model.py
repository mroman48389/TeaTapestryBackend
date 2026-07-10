import uuid
from sqlalchemy import Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from datetime import datetime, timezone

from src.db.base import Base

# SQLAlchemy blueprint for database table. This schema defines how data is stored in the database.
class UserTeaProfileNotesModel(Base):
    # SQLAlchemy needs this dunder to be called tablename to do its mapping.
    __tablename__ = "user_tea_profile_notes"

    # Always use UUID for ids corresponding to user data.
    #
    # PG_UUID gives better performance, native UUID storage, and no casting issues for Postgres,
    # and SQLite accepts it.
    #
    # default = uuid.uuid4 will auto generate a new UUID when a new user is added. Note this is 
    # a function reference so that SQLAlchemy generates a new UUID each time.
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid = True), 
        primary_key = True, 
        default = uuid.uuid4,
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid = True),
        ForeignKey("users.id", ondelete = "CASCADE"),
        nullable = False
    )

    tea_profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tea_profiles.id", ondelete = "CASCADE"),
        nullable = False
    )

    # DateTime(timezone = True) and datetime.now(timezone.utc) give us 
    # timezone-aware UTC timestamps.
    #
    # Again, we use a lambda function to pass the function reference so SQLAlchemy 
    # generates a new datetime each time.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        default = lambda: datetime.now(timezone.utc),
        nullable = False,
    )

    # onupdate = lambda: datetime.now(timezone.utc) means every time the user row 
    # is updated, updated_at will be set to the current UTC timestamp.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        default = lambda: datetime.now(timezone.utc),
        onupdate = lambda: datetime.now(timezone.utc),
        nullable = False,
    )

    ################################################

    # ex: Dragon Well is Longjing, Lung Ching as well.
    alternative_names: Mapped[str] = mapped_column(Text, default = "")

    # ex: Qunti Zhong, Longjing #43 for Dragon Well
    cultivars: Mapped[str] = mapped_column(Text, default = "")

    # pan-fired, steamed, scented/flavored, etc,
    processing: Mapped[str] = mapped_column(Text, default = "")

    # ex: Dragonwell is very low (typically 0%)
    oxidation_level: Mapped[str] = mapped_column(Text, default = "")

    # top 10 famous Chinese tea? geographically protected? story behind name,
    # etc.
    cultural_significance: Mapped[str] = mapped_column(Text, default = "")

    cultural_significance_source: Mapped[str] = mapped_column(Text, default = "")

    # As much info as available, such as Hangzhou (city), Zhejiang (province)
    # for Dragon Well
    subregions: Mapped[str] = mapped_column(Text, default = "")

    liquor_appearance: Mapped[str] = mapped_column(Text, default = "")

    liquor_aroma: Mapped[str] = mapped_column(Text, default = "")
    # includes aftertaste, hui gan, etc,
    liquor_taste: Mapped[str] = mapped_column(Text, default = "")

    # includes astringency, etc,
    liquor_body_mouthfeel: Mapped[str] = mapped_column(Text, default = "")
    # calming, mouth-watering, alert, astringent, etc.
    body_effect: Mapped[str] = mapped_column(Text, default = "")

    # flat, curled, rolled, different color shades, relative leaf size, etc.
    dry_leaf_appearance: Mapped[str] = mapped_column(Text, default = "")
    dry_leaf_aroma: Mapped[str] = mapped_column(Text, default = "")

    wet_leaf_appearance: Mapped[str] = mapped_column(Text, default = "")
    wet_leaf_aroma: Mapped[str] = mapped_column(Text, default = "")

    # SQL:
    #
    # CREATE TABLE tea_profiles (
    #     id SERIAL PRIMARY KEY,
    #
    #     alternative_names TEXT,
    #     cultivars TEXT,
    #     processing TEXT,
    #     oxidation_level TEXT,
    #     cultural_significance TEXT,
    #     cultural_significance_source TEXT
    #
    #     subregions TEXT,
    #
    #     liquor_appearance TEXT,
    #     liquor_aroma TEXT,
    #     liquor_taste TEXT,
    #     liquor_body_mouthfeel TEXT,
    #     body_effect TEXT,
    #
    #     dry_leaf_appearance TEXT,
    #     dry_leaf_aroma TEXT,

    #     wet_leaf_appearance TEXT,
    #     wet_leaf_aroma TEXT
    # );
    #
    #
    # Note that SERIAL is an auto-incrementing INTEGER
