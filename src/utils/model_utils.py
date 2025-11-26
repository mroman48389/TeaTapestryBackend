from sqlalchemy import Numeric, Text, String
from sqlalchemy.types import TypeEngine

def get_model_column_names(model, include_primary_key: bool = True) -> list[str]:
    return [col.name for col in model.__table__.columns if 
        (not col.primary_key) or include_primary_key]

def get_model_column_names_as_str(model, include_primary_key: bool = True) -> str:
    return ", ".join(get_model_column_names(model, include_primary_key))

# TypeEngine is the abstract base class from which all concrete types like
# String and Integer inherit from.
def get_dtype_mapping(model) -> dict[str, TypeEngine]:
    dtype_map = {}

    # Map columns that Pandas might misinterpret to dtypes.
    # Useful when pushing the Pandas DataFrame into the
    # SQLAlchemy database.
    for col in model.__table__.columns:

        if isinstance(col.type, (String, Text)):
            # Map text columns explicitly to SQLAlchemy Text.
            # This ensures Python None values are stored as proper SQL NULLs
            # instead of empty strings. In Postgres, NULL is the correct
            # representation of "no data." pgAdmin displays these as [null].
            dtype_map[col.name] = Text() 

        elif isinstance(col.type, Numeric):
            dtype_map[col.name] = Numeric()

    return dtype_map