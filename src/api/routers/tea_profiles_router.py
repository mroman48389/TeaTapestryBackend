from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import List, get_origin, get_args, Union

from src.utils.session_utils import get_session
from src.api.schemas.tea_profiles_schema import TeaProfileSchema, TeaProfileFilters
from src.api.constants.responses import COMMON_RESPONSES
from src.db.repositories.tea_profiles_repository import TeaProfilesRepository

# Define group of routes with api/tea_profiles as their base path and tea_profiles
# for documentation grouping.
router = APIRouter(prefix="/api/v1/tea_profiles", tags=["tea_profiles"])

# Custom FastAPI dependency so that we can set up TeaProfileFilters as a query
# rather than a body in out route below. Looks at the query string of an incoming
# request (ex: ?country_of_origin=China&oxidation_level=green), grab the 
# parameters that match fields in the TeaProfileFilters schema, and use them to
# build a TeaProfileFilters Pydantic model instance that the route can use.
def get_tea_profile_filters(request: Request) -> TeaProfileFilters: # type: ignore
    params = {}

    # for field_name, field_info in TeaProfileFilters.model_fields.items():
    #     # See if the field from the TeaProfileFilters schema exists in the 
    #     # dictionary-like object containing every parameter after the ? in the
    #     # URL.
    #     value = request.query_params.get(field_name)

    #     # If it was found, add it to the params dict we're building.
    #     if value is not None:
    #         # Handle list types first. Split on commas.
    #         if get_origin(field_info.annotation) is list:
    #             # Normalize into a Python list
    #             params[field_name] = [v.strip() for v in value.split(",")]
    #         else:
    #             params[field_name] = value

    for field_name, field_info in TeaProfileFilters.model_fields.items():
        value = request.query_params.get(field_name)
        if value is not None:
            origin = get_origin(field_info.annotation)
            args = get_args(field_info.annotation)

            # If it's Optional[List[str]], origin will be Union and args will include list
            if origin is Union and any(get_origin(arg) is list for arg in args):
                params[field_name] = [v.strip() for v in value.split(",")]

            else:
                params[field_name] = value

    # Return a Pydantic model with the provided filters.
    return TeaProfileFilters(**params)

# Depends is FastAPI's dependency injection system. It allows us to call the 
# get_session context manager without needing to use a "with" statement or
# other boilerplate code in every route that needs it. FastAPI handles the 
# lifecycle management (opening, closing sessions) for us. Using Depends 
# also makes it easier to swap dependencies in tests. Swagger/OpenAPI docs will
# also show that the routes depend on a database session when we use Depends.
#
# Note that FastAPI/SwaggerUI treats parameters as either body or query depending on how
# they are passed. For GETs, we want query params, since GETs should not
# have bodies. Ex:
#
# def get_x(filters: TeaProfileFilters):             # body
# def get_x(filters: TeaProfileFilters = Depends()): # query
# def get_x(limit: int = Query(10)):                 # query

@router.get("/", response_model = List[TeaProfileSchema], 
    responses = COMMON_RESPONSES # type: ignore
)
def get_tea_profiles(
    filters: TeaProfileFilters = Depends(get_tea_profile_filters), # type: ignore
    session: Session = Depends(get_session),
    limit: int = 100,
    offset: int = 0
):
    repo = TeaProfilesRepository(session)
    # filters.model_dump(exclude_none = True) returns the Pydantic model as a
    # dict, dropping all fields that have a value of None. 
    #
    # TeaProfileFilters does not belong in TeaProfilesRepository (it's part of the API layer,
    # as it's a Pydantic request schema), so save the dict returned by model_dump here and 
    # pass that along rather than the schema itself.
    filters_dict = filters.model_dump(exclude_none = True)
    tea_profiles = repo.list(filters = filters_dict, limit = limit, offset = offset)
    return tea_profiles

@router.get("/{tea_profile_id}", response_model = TeaProfileSchema, 
    responses = COMMON_RESPONSES # type: ignore
)
def get_tea_profile(tea_profile_id: int, session: Session = Depends(get_session)):
    '''Gets an entire tea profile for one tea.'''
    repo = TeaProfilesRepository(session)
    tea_profile = repo.get_by_id(tea_profile_id)
    return tea_profile