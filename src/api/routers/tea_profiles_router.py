from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Annotated

from src.utils.session_utils import get_session
from src.db.models.tea_profiles_model import TeaProfileModel
from src.api.schemas.tea_profiles_schema import TeaProfileSchema, TeaProfileFilters

# Define group of routes with api/tea_profiles as their base path and tea_profiles
# for documentation grouping.
router = APIRouter(prefix="/api/v1/tea_profiles", tags=["tea_profiles"])

# Depends is FastAPI's dependency injection system. It allows us to call the 
# get_session context manager without needing to use a "with" statement or
# other boilerplate code in every route that needs it. FastAPI handles the 
# lifecycle management (opening, closing sessions) for us. Using Depends 
# also makes it easier to swap dependencies in tests. Swagger/OpenAPI docs will
# also show that the routes depend on a database session when we use Depends.

@router.get("/", response_model = List[TeaProfileSchema])
def get_tea_profiles(
    filters: Annotated[TeaProfileFilters, Depends()], # type: ignore
    session: Session = Depends(get_session),
    limit: int = 10,
    offset: int = 0
):
    '''Gets a list of tea profiles with the provided filters.'''
    # Get a query object that will allow us to ask the database for data,
    # extracting it as ORM objects of type TeaProfileModel.
    query = session.query(TeaProfileModel)

    # filters.model_dump(exclude_none = True) returns the Pydantic model as a
    # dict, dropping all fields that have a value of None. field_name will be
    # something like "country_of_origin" and value will be something like "China".
    # Each loop will further refine the query. 
    for field_name, value in filters.model_dump(exclude_none = True).items():
        # getattr(TeaProfileModel, field_name) will grab the the column object.
        # So, for example, TeaProfileModel.country_of_origin. 
        query = query.filter(getattr(TeaProfileModel, field_name) == value)

    # Return "limit" number of rows starting on row "offset" that satisfy the query.
    teas_profiles = query.offset(offset).limit(limit).all()

    # In raw SQL, our queries would look something like this:
    #
    #     SELECT * FROM tea_profiles
    #     WHERE oxidation_level = 'green' AND country_of_origin = 'China'
    #     LIMIT 10 OFFSET 0;

    return teas_profiles

@router.get("/{tea_profile_id}", response_model = TeaProfileSchema)
def get_tea_profile(tea_profile_id: int, session: Session = Depends(get_session)):
    '''Gets an entire tea profile for one tea.'''
    tea_profile = session.get(TeaProfileModel, tea_profile_id)

    if not tea_profile:
        raise HTTPException(
            status_code = 404, 
            detail = "A tea profile with the provided id was not found"
        )
    
    return tea_profile