from sqlalchemy import Column, DateTime

from src.utils.sample_data_utils import init_sample_tea_profiles_row
from src.db.models.tea_profiles_model import TeaProfileModel

def test_init_sample_tea_profiles_row_else(monkeypatch):
    original_columns = TeaProfileModel.__table__.columns

    date_time_col = Column("created_at", DateTime)

    # Add a new column to the TeaProfile model that has a type that
    # will only get covered by the else catch-all at the end of the
    # function.
    monkeypatch.setattr(
        TeaProfileModel.__table__,
        "columns",
        list(original_columns) + [date_time_col]
    )

    row = init_sample_tea_profiles_row({})
    assert row["created_at"] is None