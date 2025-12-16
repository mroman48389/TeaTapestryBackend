from starlette import status

COMMON_RESPONSES = {
    status.HTTP_200_OK: {"description": "Success"},
    status.HTTP_404_NOT_FOUND: {"description": "Not found"},
    status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error"},
}