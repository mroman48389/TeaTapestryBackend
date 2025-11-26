import pytest

from sqlalchemy import Column, Integer, String, Table, MetaData
from sqlalchemy.dialects.postgresql import ARRAY

from src.utils.csv_utils import (
    parse_array, parse_numeric, parse_string, load_and_clean_csv
)
from src.constants.model_metadata_constants import DELIMITER_VALUE

@pytest.mark.parametrize(
    "value, delimiter, expected",
    [
        ("a; b; c", DELIMITER_VALUE, ["a", "b", "c"]),  # normal case
        ("a, b, c", ",", ["a", "b", "c"]),              # custom delimiter
        ("", ",", []),                                  # empty string
        ("   ", ",", []),                               # whitespace-only
        (None, ",", []),                                # None
        (5, ",", []),                                   # wrong type
    ]
)
def test_parse_array(value, delimiter, expected):
    assert parse_array(value, delimiter) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("5", 5),         # normal case
        ("", None),       # empty string
        ("   ", None),    # whitespace-only
        (None, None),     # None
        ("test", None),   # wrong type
        (5, None)         # wrong type
    ]
)
def test_parse_numeric(value, expected):
    assert parse_numeric(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("test", "test"),                         # normal case
        (" This is a test. ", "This is a test."), # normal case
        ("", None),                               # normal case
        ("   ", None),                            # normal case
        (None, None),                             # None
        (5, None)                                 # wrong type
    ]
)
def test_parse_string(value, expected):
    assert parse_string(value) == expected


class FakeModel:
    __table__ = \
        Table(
            "test_table",
            MetaData(),
            Column("id", Integer, primary_key = True),
            Column("tags", ARRAY(String)), 
        )

@pytest.mark.parametrize("csv_data", [
    'id,tags\n1,"a,b,c"\n2,"x,y,z"\n'
])
def test_load_and_clean_csv_array(tmp_path, csv_data):
    # Write CSV to temp file
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(csv_data)

    df = load_and_clean_csv(
        csv_path = str(csv_path),
        model = FakeModel,
        required_fields = ["tags"],
        conflict_cols = ["tags"]
    )

    # The first data row (index 0), in column "tags", should exist as a list,
    # and that list should have a value of ["a", "b", "c"]. Recall that the
    # column names are not part of the row indexing and the first row of data
    # starts at row 0.
    assert isinstance(df.loc[0, "tags"], list)
    assert df.loc[0, "tags"] == ["a,b,c"]