# This file holds OpenAPI response metadata. It standardizes the shape of 
# documented responses for routers. Use for GET, HEAD, list, detail endpoints.
# Don't use for POST endpoints returning 201, DELETE endpoints returning 204,
# or endpoints that require more custom or domain-specific errors. Or endpoints
# that intentionally hide 404s like in password reset.

from starlette import status

COMMON_RESPONSES = {
    status.HTTP_200_OK: {"description": "Success"},
    status.HTTP_404_NOT_FOUND: {"description": "Not found"},
    status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error"},
}