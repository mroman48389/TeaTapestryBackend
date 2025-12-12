from sqlalchemy.types import TypeEngine
from sqlalchemy import Column, Integer, String, Table, MetaData, Boolean

from src.db.base import Base
from src.db.types.sqlite_compatible_array import SQLiteCompatibleArray

class UnsupportedType(TypeEngine):
    @property
    def python_type(self):
        raise NotImplementedError
    

# class FakeModel:
#     __table__ = \
#         Table(
#             "fake_model_table",
#             MetaData(),
#             Column("id", Integer, primary_key = True),
#             Column("tags", ARRAY(String)), 
#         )
class FakeModel(Base):
    __tablename__ = "fake_model_table"
    id = Column(Integer, primary_key = True)
    tags = Column(SQLiteCompatibleArray(String))
    active = Column(Boolean)

class UnsupportedTypeModel: 
    __table__ = \
        Table(
            "unsupported_type_model_table",
            MetaData(),
            Column("id", Integer, primary_key = True),
            Column("unsupported", UnsupportedType(), nullable = False),
        )