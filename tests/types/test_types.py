from sqlalchemy.types import TypeEngine
from sqlalchemy import Column, Integer, String, Table, MetaData
from sqlalchemy.dialects.postgresql import ARRAY

class UnsupportedType(TypeEngine):
    @property
    def python_type(self):
        raise NotImplementedError
    
class FakeModel:
    __table__ = \
        Table(
            "fake_model_table",
            MetaData(),
            Column("id", Integer, primary_key = True),
            Column("tags", ARRAY(String)), 
        )
    
class UnsupportedTypeModel: 
    __table__ = \
        Table(
            "unsupported_type_model_table",
            MetaData(),
            Column("id", Integer, primary_key = True),
            Column("unsupported", UnsupportedType(), nullable = False),
        )