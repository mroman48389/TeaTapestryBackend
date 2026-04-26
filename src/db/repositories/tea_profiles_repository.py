# Layer 3 (Database/SQLAlchemy/bottomost layer): This is where error handling starts. We
# catch raw SQLAlchemy errors and convert them into the domain errors that layer 2 deals
# with. This layer ensures raw SQL errors don't reach layer 1.

from __future__ import annotations

from typing import List, Mapping, Any
# later, once the user can add their own tea profiles: from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import String, Text, func

from src.db.types.sqlite_compatible_array import SQLiteCompatibleArray
# later, once the user can add their own tea profiles: TeaProfileConflictError
from src.app.errors import (
    TeaProfileNotFoundError,
    TeaProfileQueryError,
)
from src.db.models.tea_profiles_model import TeaProfileModel 
from src.utils.sql_dialect_utils import get_sql_from_dialect

# A repository is a class tasked with talking to a database and returning domain objects. It
# should be the only place on the backend that knows how to query the DB, insert/update/delete,
# translate SQLAlchemy errors, and manage transactions. 
# 
# It's a class rather than a set of functions because it needs to work on a database session. 
# Without it, we'd need to pass a session into each function of said set. It's useful for testing.
class TeaProfilesRepository:

    # Store database session.
    def __init__(self, session: Session) -> None:
        self._session = session

    # Get a tea profile with a particular id.
    def get_by_id(self, tea_profile_id: int) -> TeaProfileModel:

        try:        
            tea_profile = self._session.get(TeaProfileModel, tea_profile_id)

            if tea_profile is None:
                raise TeaProfileNotFoundError(
                    f"A tea profile with id {tea_profile_id} was not found.",
                    details={"id": tea_profile_id}
                )
            
            return tea_profile
        
        except SQLAlchemyError as exc:
            raise TeaProfileQueryError(
                "Failed to fetch tea profile",
                details={"id": tea_profile_id},
            ) from exc

    # Get multiple tea profiles.
    def list(self, filters: Mapping[str, Any], 
        limit: int = 100, offset: int = 0) -> List[TeaProfileModel]:

        try:        
            # Get a query object that will allow us to ask the database for data,
            # extracting it as ORM objects of type TeaProfileModel.
            query = self._session.query(TeaProfileModel)

            # field_name will be something like "country_of_origin" and value will be something like "China".
            # Each loop will further refine the query. 
            for field_name, value in filters.items():
                column = getattr(TeaProfileModel, field_name)

                # Normalize to lowercase for case-insensitive matching
                # and split comma-separated filters into multiple values
                if isinstance(value, str):
                    value = [v.strip().lower() for v in value.split(",")]
                else:
                    value = [str(v).lower() for v in value]

                # ---------------------------------------------------------
                # 1. ARRAY fields (PostgreSQL or SQLiteCompatibleArray)
                # ---------------------------------------------------------

                if isinstance(column.type, ARRAY) or isinstance(column.type, SQLiteCompatibleArray):
                    # PostgreSQL: use ANY() with ILIKE
                    if get_sql_from_dialect(self._session, "postgresql", "sqlite") == "postgresql":
                        for v in value:
                            query = query.filter(
                                func.lower(column).any(v, operator="ilike")
                            )
                    else:
                        # SQLite fallback: stored as JSON-like text --> substring match
                        for v in value:
                            query = query.filter(func.lower(column).like(f"%{v}%"))

                # ---------------------------------------------------------
                # 2. String fields: Do a case-insensitive substring match.
                # ---------------------------------------------------------

                elif isinstance(column.type, String) or isinstance(column.type, Text):
                    for v in value:
                        query = query.filter(func.lower(column).like(f"%{v}%"))

                # ---------------------------------------------------------
                # 3. Everything else: Look for an exact match.
                # ---------------------------------------------------------

                else:
                    query = query.filter(column == value)

            # Return "limit" number of rows starting on row "offset" that satisfy the query.
            teas_profiles = query.offset(offset).limit(limit).all()

            # In raw SQL, our queries would look something like this:
            #
            #     SELECT * FROM tea_profiles
            #     WHERE oxidation_level = 'green' AND country_of_origin = 'China'
            #     LIMIT 10 OFFSET 0;

            return teas_profiles
        
        except SQLAlchemyError as exc:
            raise TeaProfileQueryError(
                "Failed to list tea profiles",
                details={"filters": filters, "limit": limit, "offset": offset},
            ) from exc

    # later, once the user can add their own tea profiles: 
    
    # Create a new tea profile.
    # def create(self, obj_in: TeaProfileModel) -> TeaProfileModel:
    #     try:
    #         self._session.add(obj_in)
    #         self._session.commit()
    #         self._session.refresh(obj_in)
    #         return obj_in
        
    #     except IntegrityError as exc:
    #         self._session.rollback()
    #         raise TeaProfileConflictError(
    #             "Tea profile conflicts with existing data",
    #             details={"name": getattr(obj_in, "name", None)},
    #         ) from exc
        
    #     except SQLAlchemyError as exc:
    #         self._session.rollback()
    #         raise TeaProfileQueryError(
    #             "Failed to create tea profile",
    #             details={"name": getattr(obj_in, "name", None)},
    #         ) from exc
