import pytest

from src.utils.csv_utils import (
    parse_array, parse_numeric, parse_string, load_and_clean_csv
)
from src.constants.model_metadata_constants import DELIMITER_VALUE
from tests.types.test_types import FakeModel


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


@pytest.mark.parametrize("csv_data, expected_active", [
    ('id, tags, active \n 1, a; b; c, false \n 2, x; y; z, true \n', [False, True]),
    ('id, tags, active \n 1, a; b; c, 0 \n 2, x; y; z, 1 \n', [False, True]),
    ('id, tags, active \n 1, a; b; c, f \n 2, x; y; z, t \n', [False, True])
])
def test_load_and_clean_csv_arrays_booleans(tmp_path, csv_data, expected_active):
    # Write CSV to temp file
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(csv_data)

    df = load_and_clean_csv(
        csv_path = str(csv_path),
        model = FakeModel,
        required_fields = ["tags", "active"],
        conflict_cols = ["tags"]
    )

    # The first data row (index 0), in column "tags", should exist as a list,
    # and that list should have a value of ["a", "b", "c"]. Recall that the
    # column names are not part of the row indexing and the first row of data
    # starts at row 0.
    assert isinstance(df.loc[0, "tags"], list)
    assert df.loc[0, "tags"] == ["a", "b", "c"]
    assert list(df["active"]) == expected_active