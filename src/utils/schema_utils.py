from typing import Optional
from pydantic import BaseModel, create_model
from sqlalchemy.types import Numeric
from src.db.types.sqlite_compatible_array import SQLiteCompatibleArray

def get_schema_from_model(model, name: str | None = None) -> type[BaseModel]:
    """Dynamically create a Pydantic schema from a SQLAlchemy model."""

    fields = {}

    # Create a dict that maps tuples containing JSON-serializable Python types 
    # to the model's field names.
    for column in model.__table__.columns:
        
        # Cover our custom type that uses ARRAY for PostgreSQL and Text for
        # SQLite so our testing suites don't break.
        if isinstance(column.type, SQLiteCompatibleArray):
            py_type = list[str]

        # SQLAlchemy's Numeric maps to Python's Decimal. JSON doesn't support
        # Decimal, so change to float.
        elif isinstance(column.type, Numeric):
            py_type = float

        else:
            try:
                # Try inferring type.
                py_type = column.type.python_type

            except NotImplementedError:
                # If the type is not implemented, make it a string as the safest
                # option.
                py_type = str

        # Pydantic models built with create_model need fields defined as tuples 
        # ((type, default) form). If the field is optional, the tuple will include 
        # the JSON-serializable  type we determined it should be or None. 
        # Otherwise, the tuple will include the type we determined.
        if column.nullable:
            fields[column.name] = (Optional[py_type], None)
        else:
            fields[column.name] = (py_type, ...)

    schema_name = name or f"{model.__name__}Schema"

    # "from_attributes": True is necessary for ORM compatibility.
    return create_model(
        schema_name,
        **fields,
        __cls_kwargs__ = {"from_attributes": True}
    )