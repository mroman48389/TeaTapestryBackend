from tests.types.test_types import UnsupportedTypeModel
from src.utils.schema_utils import get_schema_from_model


def test_get_schema_from_model_handles_not_implemented_error():

    # Create schema from model.
    schema = get_schema_from_model(model = UnsupportedTypeModel, name = "DummySchema")

    # If get_schema_from_model hits the exception as expected, the unsupported 
    # column should be of type str. 
    assert schema.model_fields["unsupported"].annotation is str