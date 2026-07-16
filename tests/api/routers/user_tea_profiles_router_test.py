from uuid import UUID
from starlette import status

from src.constants.route_constants import USER_TEA_PROFILE_NOTES_PREFIX
from tests.utils.test_utils import (
    get_auth_headers, 
    get_empty_user_tea_profile_notes_body
)

# ---------------------------------------------------------
# GET ONE
# ---------------------------------------------------------

class TestGetUserTeaProfileNotesForTea:

    def test_get_user_tea_profile_notes_for_tea_success(
        self,
        client,
        seed_user_tea_profile_notes,
        access_token_for_test_user,
        refresh_token_for_test_user,
    ):
        # Get the row we just created.
        response = client.get(
            f"{USER_TEA_PROFILE_NOTES_PREFIX}/{seed_user_tea_profile_notes.tea_profile_id}",
            headers = get_auth_headers(access_token_for_test_user, refresh_token_for_test_user)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == str(seed_user_tea_profile_notes.id)


    def test_get_user_tea_profile_notes_for_tea_not_found(
        self,
        client,
        access_token_for_test_user,
        refresh_token_for_test_user
    ):
        response = client.get(
            f"{USER_TEA_PROFILE_NOTES_PREFIX}/999999",
            headers = get_auth_headers(access_token_for_test_user, refresh_token_for_test_user)
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------
# GET ALL
# ---------------------------------------------------------

class TestGetAllUserTeaProfileNotes:

    def test_get_all_user_tea_profile_notes_empty(
        self,
        client,
        access_token_for_test_user,
        refresh_token_for_test_user
    ):
        response = client.get(
            f"{USER_TEA_PROFILE_NOTES_PREFIX}/",
            headers = get_auth_headers(access_token_for_test_user, refresh_token_for_test_user)
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


    def test_get_all_user_tea_profile_notes_non_empty(
        self,
        client,
        seed_user_tea_profile_notes,
        access_token_for_test_user,
        refresh_token_for_test_user,
    ):
        response = client.get(
            f"{USER_TEA_PROFILE_NOTES_PREFIX}/",
            headers = get_auth_headers(access_token_for_test_user, refresh_token_for_test_user)
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(seed_user_tea_profile_notes.id)

# ---------------------------------------------------------
# CREATE
# ---------------------------------------------------------

class TestCreateUserTeaProfileNotes:

    def test_create_user_tea_profile_notes_success(
        self,
        client,
        access_token_for_test_user,
        refresh_token_for_test_user,
        long_jing_tea_profile_id
    ):
        response = client.post(
            f"/api/v1/user_tea_profile_notes/{long_jing_tea_profile_id}",
            json = get_empty_user_tea_profile_notes_body(),
            headers = get_auth_headers(access_token_for_test_user, refresh_token_for_test_user)
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["tea_profile_id"] == long_jing_tea_profile_id
        assert UUID(data["id"])


    def test_create_user_tea_profile_notes_duplicate_fails(
        self,
        client,
        access_token_for_test_user,
        refresh_token_for_test_user,
        long_jing_tea_profile_id
    ):
        body = get_empty_user_tea_profile_notes_body()

        # First create should work.
        client.post(
            f"{USER_TEA_PROFILE_NOTES_PREFIX}/{long_jing_tea_profile_id}",
            json = body,
            headers = get_auth_headers(access_token_for_test_user, refresh_token_for_test_user)
        )

        # Second create should fail.
        response = client.post(
            f"{USER_TEA_PROFILE_NOTES_PREFIX}/{long_jing_tea_profile_id}",
            json = body,
            headers = get_auth_headers(access_token_for_test_user, refresh_token_for_test_user)
        )

        assert response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT)

# ---------------------------------------------------------
# UPDATE
# ---------------------------------------------------------

class TestUpdateUserTeaProfileNotes:

    def test_update_user_tea_profile_notes_success(
        self,
        client,
        seed_user_tea_profile_notes,
        access_token_for_test_user,
        refresh_token_for_test_user,
    ):
        response = client.patch(
            f"{USER_TEA_PROFILE_NOTES_PREFIX}/{seed_user_tea_profile_notes.id}",
            json = {"liquor_taste": "sweet"},
            headers = get_auth_headers(access_token_for_test_user, refresh_token_for_test_user)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["liquor_taste"] == "sweet"


    def test_update_user_tea_profile_notes_not_found(
        self,
        client,
        access_token_for_test_user,
        refresh_token_for_test_user
    ):
        response = client.patch(
            f"{USER_TEA_PROFILE_NOTES_PREFIX}/00000000-0000-0000-0000-000000000000",
            json = {"liquor_taste": "sweet"},
            headers = get_auth_headers(access_token_for_test_user, refresh_token_for_test_user)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------
# DELETE
# ---------------------------------------------------------

class TestDeleteUserTeaProfileNotes:

    def test_delete_user_tea_profile_notes_success(
        self,
        client,
        seed_user_tea_profile_notes,
        access_token_for_test_user,
        refresh_token_for_test_user,
    ):
        note_id = seed_user_tea_profile_notes.id
        tea_profile_id = seed_user_tea_profile_notes.tea_profile_id

        # Delete the starting tea.
        response = client.delete(
            f"{USER_TEA_PROFILE_NOTES_PREFIX}/{note_id}",
            headers = get_auth_headers(access_token_for_test_user, refresh_token_for_test_user)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Confirm deletion
        get_resp = client.get(
            f"{USER_TEA_PROFILE_NOTES_PREFIX}/{tea_profile_id}",
            headers = get_auth_headers(access_token_for_test_user, refresh_token_for_test_user)
        )
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND


    def test_delete_user_tea_profile_notes_not_found(
        self,
        client,
        access_token_for_test_user,
        refresh_token_for_test_user
    ):
        response = client.delete(
            f"{USER_TEA_PROFILE_NOTES_PREFIX}/00000000-0000-0000-0000-000000000000",
            headers = get_auth_headers(access_token_for_test_user, refresh_token_for_test_user)
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
