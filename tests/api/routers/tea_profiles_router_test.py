import pytest
from starlette import status

from src.api.schemas.tea_profiles_schema import TeaProfileSchema
from src.constants.tea_profiles_constants import TeaProfileModelFields

def test_get_tea_profiles(client, seed_tea_profiles):
    filters = {
        TeaProfileModelFields.TEA_TYPE: "green",
        TeaProfileModelFields.COUNTRY_OF_ORIGIN: "China",
        TeaProfileModelFields.ALTERNATIVE_NAMES: "Dragonwell,Dragon Well"
    }
    response = client.get("/api/v1/tea_profiles", params = filters)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) >= 1

    for tea_profile in data:
        value = TeaProfileSchema.model_validate(tea_profile)
        assert isinstance(value, TeaProfileSchema)
        assert tea_profile[TeaProfileModelFields.TEA_TYPE] == "green"
        assert tea_profile[TeaProfileModelFields.COUNTRY_OF_ORIGIN] == "China"
        assert tea_profile[TeaProfileModelFields.ALTERNATIVE_NAMES] == ["Dragonwell", "Dragon Well"]

def test_head_tea_profiles(client, seed_tea_profiles):
    filters = {
        TeaProfileModelFields.TEA_TYPE: "green",
        TeaProfileModelFields.COUNTRY_OF_ORIGIN: "China",
        TeaProfileModelFields.ALTERNATIVE_NAMES: "Dragonwell,Dragon Well"
    }

    response = client.head("/api/v1/tea_profiles", params=filters)

    # HEAD should behave like GET but with no body
    assert response.status_code == status.HTTP_200_OK
    assert response.text == ""  # no body

    # Must include caching headers
    assert "ETag" in response.headers
    assert "Last-Modified" in response.headers
    assert "Cache-Control" in response.headers
    
def test_get_tea_profiles_limit_clamping(client, seed_tea_profiles):
    response = client.get("/api/v1/tea_profiles?limit=9999")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    # Should clamp to 200 max
    assert len(data) <= 200

######################################################################################################



# "long jing id"       --> normal case; integer for existing tea profile. 
#                          Note that we can't use hardcoded ids because our
#                          ids may differ for the same tea in our actual and 
#                          testing databases. So we use a fixture that grabs the
#                          id after we know ingestion has happened and a placeholder
#                          in the parametrization.
# -1                   --> tea profile id does not exist (PostgreSQL will never
#                          autogenerate negative numbers, so this is a safe integer
#                          test)
# "abc"                --> FastAPI will try to convert to int and not be able to; 
#                          breaks contract
@pytest.mark.parametrize(
    "id, expected_status",
    [
        ("long jing id", status.HTTP_200_OK),   
        (-1, status.HTTP_404_NOT_FOUND),    
        ("abc", status.HTTP_422_UNPROCESSABLE_CONTENT),    
    ]
)

def test_get_tea_profile(client, long_jing_tea_profile_id, id, expected_status):
    # Replace placeholder with fixture value
    if id == "long jing id":
        id = long_jing_tea_profile_id

    response = client.get(f"/api/v1/tea_profiles/{id}")
    assert response.status_code == expected_status

    data = response.json()

    if expected_status == status.HTTP_200_OK:
        # Check to make sure the data adheres to the expected schema.
        tea_profile = TeaProfileSchema.model_validate(data)
        assert isinstance(tea_profile, TeaProfileSchema)

    elif expected_status == status.HTTP_404_NOT_FOUND:
        assert data["error"]["message"] == f"A tea profile with id {id} was not found."

    elif expected_status == status.HTTP_422_UNPROCESSABLE_CONTENT:
        assert data["detail"][0]["type"] == "int_parsing"
        # Make sure the error is specifically tied to the tea_profile_id param and
        # not something else like a query param or request body.
        assert data["detail"][0]["loc"] == ["path", "tea_profile_id"]

def test_head_tea_profile(client, long_jing_tea_profile_id):
    response = client.head(f"/api/v1/tea_profiles/{long_jing_tea_profile_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.text == ""  # HEAD returns no body

    assert "ETag" in response.headers
    assert "Last-Modified" in response.headers
    assert "Cache-Control" in response.headers

def test_head_tea_profile_not_found(client):
    response = client.head("/api/v1/tea_profiles/-1")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.text == ""  # still no body for HEAD

def test_head_tea_profile_invalid_id_type(client):
    response = client.head("/api/v1/tea_profiles/abc")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.text == ""  # HEAD returns no body

def test_get_tea_profile_if_none_match_returns_304(client, long_jing_tea_profile_id):
    # First GET to obtain ETag
    first = client.get(f"/api/v1/tea_profiles/{long_jing_tea_profile_id}")
    assert first.status_code == status.HTTP_200_OK
    etag = first.headers.get("ETag")
    assert etag is not None

    # Second GET with If-None-Match
    second = client.get(
        f"/api/v1/tea_profiles/{long_jing_tea_profile_id}",
        headers={"If-None-Match": etag}
    )

    assert second.status_code == status.HTTP_304_NOT_MODIFIED
    assert second.text == ""

def test_get_tea_profile_if_modified_since_returns_304(client, long_jing_tea_profile_id):
    # First GET to obtain Last-Modified
    first = client.get(f"/api/v1/tea_profiles/{long_jing_tea_profile_id}")
    assert first.status_code == status.HTTP_200_OK
    last_modified = first.headers.get("Last-Modified")
    assert last_modified is not None

    # Second GET with If-Modified-Since equal to Last-Modified
    second = client.get(
        f"/api/v1/tea_profiles/{long_jing_tea_profile_id}",
        headers={"If-Modified-Since": last_modified}
    )

    assert second.status_code == status.HTTP_304_NOT_MODIFIED
    assert second.text == ""

def test_get_tea_profile_cache_hit(client, long_jing_tea_profile_id):
    # First GET populates cache
    first = client.get(f"/api/v1/tea_profiles/{long_jing_tea_profile_id}")
    assert first.status_code == status.HTTP_200_OK

    etag_1 = first.headers.get("ETag")
    lm_1 = first.headers.get("Last-Modified")

    # Second GET should hit cache and return same headers
    second = client.get(f"/api/v1/tea_profiles/{long_jing_tea_profile_id}")
    assert second.status_code == status.HTTP_200_OK

    etag_2 = second.headers.get("ETag")
    lm_2 = second.headers.get("Last-Modified")

    assert etag_1 == etag_2
    assert lm_1 == lm_2