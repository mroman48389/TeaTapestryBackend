from sqlalchemy import String, Integer, Column
from pydantic import BaseModel

from src.db.base import Base
from src.utils.serialization import to_serializable

def test_to_serializable_pydantic():
    class PydanticModel(BaseModel):
        a: int
        b: str

    model = PydanticModel(a = 1, b = "x")
    result = to_serializable(model)

    assert result == {"a": 1, "b": "x"}

def test_to_serializable_sqlalchemy():
    class SQLAlchemyModel(Base):
        __tablename__ = "sqlalchemy_model"

        id = Column(Integer, primary_key = True)
        name = Column(String)

    obj = SQLAlchemyModel(id = 1, name = "chair")
    result = to_serializable(obj)

    assert result == {"id": 1, "name": "chair"}

def test_to_serializable_list():
    data = [1, "x", {"y": 2}]
    result = to_serializable(data)

    assert result == [1, "x", {"y": 2}]

def test_to_serializable_primitive():
    assert to_serializable(5) == 5
    assert to_serializable("x") == "x"
