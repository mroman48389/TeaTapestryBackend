import pytest
from starlette import status

from src.api.schemas.tea_profiles_schema import TeaProfileSchema
from src.constants.tea_profiles_constants import TeaProfileModelFields
from tests.utils.test_utils import get_id_from_tea_name

def test_get_tea_profiles(client):
    filters = {
        TeaProfileModelFields.TEA_TYPE: "green",
        TeaProfileModelFields.COUNTRY_OF_ORIGIN: "China"
    }
    response = client.get("/api/v1/tea_profiles", params = filters)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    for tea_profile in data:
        value = TeaProfileSchema.model_validate(tea_profile)
        assert isinstance(value, TeaProfileSchema)
        assert tea_profile[TeaProfileModelFields.TEA_TYPE] == "green"
        assert tea_profile[TeaProfileModelFields.COUNTRY_OF_ORIGIN] == "China"

# get_id_from_tea_name --> normal case; integer for existing tea profile. 
#                          Note that we can't use hardcoded examples because our
#                          ids may differ for the same tea in our actual and 
#                          testing databases.
# 1                    --> tea profile id does not exist
# "abc"                --> FastAPI will try to convert to int and not be able to; 
#                          breaks contract
@pytest.mark.parametrize(
    "id, expected_status",
    [
        (get_id_from_tea_name("Long Jing"), status.HTTP_200_OK),   
        (1, status.HTTP_404_NOT_FOUND),    
        ("abc", status.HTTP_422_UNPROCESSABLE_CONTENT),    
    ]
)
def test_get_tea_profile(client, id, expected_status):
    response = client.get(f"/api/v1/tea_profiles/{id}")
    assert response.status_code == expected_status

    data = response.json()

    if expected_status == status.HTTP_200_OK:
        # Check to make sure the data adheres to the expected schema.
        tea_profile = TeaProfileSchema.model_validate(data)
        assert isinstance(tea_profile, TeaProfileSchema)

    elif expected_status == status.HTTP_404_NOT_FOUND:
        assert data["detail"] == "A tea profile with the provided id was not found"

    elif expected_status == status.HTTP_422_UNPROCESSABLE_CONTENT:
        assert data["detail"][0]["type"] == "int_parsing"
        # Make sure the error is specifically tied to the tea_profile_id param and
        # not something else like a query param or request body.
        assert data["detail"][0]["loc"] == ["path", "tea_profile_id"]