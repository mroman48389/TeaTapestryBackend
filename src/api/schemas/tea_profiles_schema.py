from pydantic import create_model
from typing import Optional, Union, get_origin, get_args

from src.db.models.tea_profiles_model import TeaProfileModel
from src.utils.schema_utils import get_schema_from_model

# Pydantic blueprint for API contract, dynamically generated from SQLAlchemy model. 
# This schema defines how data is exposed through our API. Models JSON structure, 
# gives type validation and serialization, and used for requests/response schemas 
# in FastAPI.
TeaProfileSchema = get_schema_from_model(TeaProfileModel)

# old, brittle way
# class TeaProfileSchema(BaseModel):
#     id: int
#     name: str
#     alternative_names: List[str] | None
#     tea_type: str
#     cultivars: List[str]
#     processing: str | None
#     oxidation_level: str | None
#     cultural_significance: str | None
#     cultural_significance_source: str | None
#     country_of_origin: str
#     subregions: List[str] | None
#     avg_price_per_oz_usd: float | None
#     liquor_appearance: List[str] 
#     liquor_aroma: List[str] 
#     liquor_taste: List[str] 
#     liquor_body_mouthfeel: List[str] | None
#     body_effect: List[str] | None
#     dry_leaf_appearance: List[str] | None
#     dry_leaf_aroma: List[str] | None
#     wet_leaf_appearance: List[str] | None
#     wet_leaf_aroma: List[str] | None

#     # This is needed so Pydantic accepts ORM objects and converts them to dicts.
#     # Otherwise, Pydantic would expect plain dicts. This allows us to return
#     # SQLAlchemy objects directly from endpoints. FastAPI will serialize them
#     # into JSON using this schema.
#     class Config:
#         orm_mode = True 

# TeaProfileFilters = create_model(
#     "TeaProfileFilters",
#     **{
#         field_name: (Optional[field.annotation], None)
#         for field_name, field in TeaProfileSchema.model_fields.items()
#     },
#     __config__ = {"from_attributes": True}
# )

def _get_tea_profile_schema_fields():
    fields = {}

    # BaseModel's model_fields is a dict that maps field names to FieldInfo 
    # objects. FieldInfo contains metadata about the field. so items() will
    # produce (field_name, FieldInfo) tuples we can pull information from. 
    for field_name, field_info in TeaProfileSchema.model_fields.items():
        annotation = field_info.annotation

        # Return the base type of a generic or union type (or None if the type
        # is not generic). Some examples:
        #
        #     get_origin(list[str])        --> <class 'list'>
        #     get_origin(Union[int, str])  --> typing.Union
        #     get_origin(int)              --> None
        #     get_origin(Optional[str])    --> typing.Union (same as str | None)
        origin = get_origin(annotation)
        
        # Return the arguments. Some examples:
        #
        #     get_args(list[str])          --> (<class 'str'>,)
        #     get_args(Union[int, str])    --> (<class 'int'>, <class 'str'>)
        #     get_args(int)                --> ()
        #     get_args(Optional[str])      --> (<class 'str'>, <class 'NoneType'>)
        args = get_args(annotation)

        # If the origin is a Union (see examples above) and NoneType is part of the
        # args, then we are dealing with an optional union type such as "str | None".
        # Use the annotation as is. We don't want to do Optional[annotation] in this
        # case, or we will end up with a nested union, which can confuse tools.
        if origin is Union and type(None) in args:
            fields[field_name] = (annotation, None)
        # Otherwise, the field is not already optional, so make it so.
        else:
            fields[field_name] = (Optional[annotation], None)

    return fields

# Create a class based on the TeaProfileSchema that will allow us to use all fields
# in TeaProfileSchema as filters.
TeaProfileFilters = create_model(
    "TeaProfileFilters",
    **_get_tea_profile_schema_fields(),
    __cls_kwargs__ = {"from_attributes": True},
)