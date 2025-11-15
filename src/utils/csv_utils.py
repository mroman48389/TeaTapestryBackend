from typing import Optional
import pandas as pd
from sqlalchemy import ARRAY, Numeric

from src.constants.model_metadata_constants import DELIMITER_KEY, IS_PRICE_KEY, DELIMITER_INFO_DICT
from src.utils.model_utils import get_model_column_names


def parse_array(value: str, delimiter: str = ";") -> list[str]:
    # If the string is not empty, return each delimited string.
    # Otherwise, return an empty array.
    return [v.strip() for v in value.split(delimiter)] if value.strip() else []


def parse_numeric(value) -> Optional[float]:
    # If the string is not empty, convert it to a float.
    # Otherwise, return None.
    return float(value) if value.strip() else None


def load_and_clean_csv(csv_path: str, model, required_fields: list[str]) -> pd.DataFrame:
    # Load CSV into dataframe.
    df = pd.read_csv(csv_path)

    # Strip white space around column headings. inplace=True ->
    # modify existing dataframe, don't create a new one.
    df.rename(columns = lambda c: c.strip(), inplace = True)

    # Drop rows missing critical fields
    df.dropna(subset = required_fields, inplace = True)

    # Drop any columns that do not exist in the model.
    df = df[get_model_column_names(model)]

    # Strip whitespace from all non-numeric values. col.dtype == "object"
    # checks that the col Series (which represents one column) is a
    # string. It is important to note that one col will have data for all
    # of the rows.
    df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

    # Note that we are looping over SQLAlchemy Column objects and the Pandas
    # DataFrame expects a string column label. Thus we do df[col.name].
    for col in model.__table__.columns:
        # Strip whitespace from each array entry.
        if isinstance(col.type, ARRAY):
            delimiter = col.info.get(
                DELIMITER_KEY, DELIMITER_INFO_DICT[DELIMITER_KEY]
            )

            df[col.name] = df[col.name].apply(
                lambda cell_contents: parse_array(cell_contents, delimiter)
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

    return df
