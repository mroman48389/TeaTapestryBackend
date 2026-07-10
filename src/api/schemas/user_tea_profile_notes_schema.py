from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

# Schemas representing user data should be explicitly created and have Inbound and Outbound 
# versions.

class UserTeaProfileNotesBaseSchema(BaseModel):
    alternative_names: str = ""
    cultivars: str = ""
    processing: str = ""
    oxidation_level: str = ""
    cultural_significance: str = ""
    cultural_significance_source: str = ""
    subregions: str = ""
    liquor_appearance: str = ""
    liquor_aroma: str = ""
    liquor_taste: str = ""
    liquor_body_mouthfeel: str = ""
    body_effect: str = ""
    dry_leaf_appearance: str = ""
    dry_leaf_aroma: str = ""
    wet_leaf_appearance: str = ""
    wet_leaf_aroma: str = ""

class UserTeaProfileNotesInboundSchema(UserTeaProfileNotesBaseSchema):
    # Prevent client from adding extra fields.
    class Config:
        extra = "forbid"

class UserTeaProfileNotesOutboundSchema(UserTeaProfileNotesBaseSchema):
    id: UUID
    tea_profile_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
