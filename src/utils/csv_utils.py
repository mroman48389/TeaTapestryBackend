from typing import Optional
import pandas as pd
import numpy as np
from sqlalchemy import ARRAY, Numeric, Text, String

from src.constants.model_metadata_constants import (
    DELIMITER_KEY, DELIMITER_VALUE, IS_PRICE_KEY
)
from src.utils.model_utils import get_model_column_names

def parse_array(value: str | None, delimiter: str = DELIMITER_VALUE) -> list[str]:
    # If the value is a string, strip whitespace
    if isinstance(value, str):
        # If the string is not empty, return each delimited string, stripped.
        # Otherwise, return an empty array.
        return [v.strip() for v in value.split(delimiter)] if value.strip() else []
    
    return []

def parse_numeric(value: str | None) -> Optional[float]:
    # If the value is a string, strip whitespace
    if isinstance(value, str):
        stripped_value = value.strip()
        # If there are any characters left after stripping,
        # return the stripped string as a float. Otherwise, return None.
        try:
            if stripped_value:
                return float(stripped_value)
        
        except ValueError:
            return None
    
    # Otherwise, return None
    return None

def parse_string(value: str | None) -> Optional[str]:
    # If the value is a string, strip whitespace
    if isinstance(value, str):
        stripped_value = value.strip()
        # If there are any characters left after stripping,
        # return the stripped string. Otherwise, return None
        # instead of an empty string. This ensures empty strings 
        # are stored as NULL, which pgAdmin renders as [null] for 
        # text. Recall that "" is falsy, so None will be returned.
        return stripped_value if stripped_value else None
    
    # Otherwise, return None
    return None

def load_and_clean_csv(csv_path: str, model, required_fields, 
    conflict_cols: list[str], delimiter: str = DELIMITER_VALUE) -> pd.DataFrame:
    
    # print("Raw CSV DataFrame before cleaning:")
    # print(pd.read_csv(csv_path))

    # Load CSV into dataframe.
    df = pd.read_csv(csv_path)

    # Normalize string "None", etc. to actual Python None
    df = df.replace({"None": None, "null": None, "NULL": None})

    # Strip white space around column headings. inplace=True ->
    # modify existing dataframe, don't create a new one.
    df.rename(columns = lambda c: c.strip(), inplace = True)

    # Drop rows missing critical fields
    df.dropna(subset = required_fields, inplace = True)

    # Drop any columns that do not exist in the model.
    df = df[get_model_column_names(model, False)]

    # Strip whitespace from all non-numeric values. col.dtype == "object"
    # checks that the col Series (which represents one column) is a
    # string. It is important to note that one col will have data for all
    # of the rows.
    df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

    # Drop duplicate entries for any data used to resolve conflicts (as this data
    # must be unique).
    df.drop_duplicates(subset = conflict_cols, inplace = True)

    # Note that we are looping over SQLAlchemy Column objects and the Pandas
    # DataFrame expects a string column label. Thus we do df[col.name].
    for col in model.__table__.columns:
        # Strip whitespace from each array entry.
        if isinstance(col.type, ARRAY):
            delimiter_value = col.info.get(DELIMITER_KEY, delimiter)

            df[col.name] = df[col.name].apply(
                lambda cell_contents: parse_array(cell_contents, delimiter_value)
                if isinstance(cell_contents, str) else cell_contents
            )

        elif isinstance(col.type, Numeric):
            # Normalize numbers, rounding prices to two decimal places.
            # Convert to a number first. This will return a NaN if the
            # cell contents are blank, which will give us the blank we
            # want in the end.
            numeric_value = pd.to_numeric(df[col.name], errors="coerce")

            if col.info.get(IS_PRICE_KEY):
                numeric_value = numeric_value.round(2)

            df[col.name] = numeric_value

        elif isinstance(col.type, String) or isinstance(col.type, Text):
            df[col.name] = df[col.name].apply(parse_string)

    # Replace any NaN values in the DataFrame with Python None.
    # This ensures that when the DataFrame is written to Postgres via SQLAlchemy,
    # those cells become proper SQL NULLs (the correct representation of "no data").
    # In pgAdmin, SQL NULLs appear as [null].
    df = df.where(pd.notnull(df), None) # type: ignore

    return df
