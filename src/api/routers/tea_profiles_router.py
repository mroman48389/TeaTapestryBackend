from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
from typing import List, get_origin, get_args, Union, cast, Any
from datetime import datetime, timezone
import sentry_sdk
from starlette import status

from src.utils.session_utils import get_session
from src.api.schemas.tea_profiles_schema import TeaProfileSchema, TeaProfileFilters
from src.api.constants.responses import COMMON_RESPONSES
from src.db.repositories.tea_profiles_repository import TeaProfilesRepository
from src.app.rate_limit import rate_limiter, HIGH_RATE_LIMIT, LOW_RATE_LIMIT
from src.cache.simple_cache import cache, CacheEntry
from src.utils.etag import generate_etag
from src.utils.date_utils import http_date
import logging

# use __name__ to get a logger named after the module we're in.
logger = logging.getLogger(__name__)

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

async def _get_tea_profiles_common(
    request: Request,
    response: Response,
    filters_dict: dict[str, Any],
    session: Session,
    limit: int,
    offset: int,
    head_only: bool = False,
):
    '''Gets all tea profiles that match the set filters, limit, and offset.'''

    # The Sentry spans througout this wrapper should only wrap the exact thing we want
    # to measure. The first span wraps the entire contents of the wrapper because it 
    # represents the entire endpoint's execution.
    with sentry_sdk.start_span(op = "endpoint", name = "tea_profiles"):
        # Enforce a maximum limit to prevent huge queries.
        limit = min(limit, 200)

        # These tags become indexed fields in Sentry that allow us to filter, group,
        # build dashboards, slice performance data, search for events, and compare 
        # traces across different values.
        #
        # Tags represent user-controlled inputs that define what the request is doing,
        # so they are typically params we pass in. They should reflect the things for
        # which performance, caching, and behavior may vary. Since these are indexed
        # by Sentry, we want high-value, low cardinality meaningful tags.
        sentry_sdk.set_tag("endpoint", "tea_profiles")
        sentry_sdk.set_tag("limit", limit)
        sentry_sdk.set_tag("offset", offset)
        sentry_sdk.set_tag("filters", str(filters_dict))

        # Build cache
        cache_key = f"tea_profiles:list:{filters_dict}:{limit}:{offset}"

        with sentry_sdk.start_span(op = "cache", name = "cache lookup"):
            # Try to get tea profiles from cache first.
            cached_entry = cache.get(cache_key)

        if cached_entry is not None:
            cached_entry = cast(CacheEntry, cached_entry)
            cached_value = cached_entry["value"]
            last_modified = cached_entry["timestamp"]

            # Optimization: ETags (Entity tags) are another caching mechanism that saves 
            # bandwidth and makes the app feel instant. The backend first sends a fingerprint of a 
            # resource (a hashed string) with its response via a header when the client 
            # makes the request. This string represents the current state of the resource. The 
            # client stores the ETag with the cached response. On subsequent requests for the same
            # resource, the client sends the ETag back in the "If-None-Match" header. The server
            # computes the current ETag for the resource. If it matches, it knows the resource 
            # hasn't changed, and it returns 304 Not Modified with no body (this is the part that
            # saves bandwidth).
            with sentry_sdk.start_span(op = "etag", name = "generate etag"):
                etag = generate_etag(cached_value)

            inm = request.headers.get("if-none-match")

            if inm == etag:
                return Response(status_code = status.HTTP_304_NOT_MODIFIED)

            # Optimization: Last-Modified is similar to ETags but uses a date instead 
            # of a hashstring fingerprint. When the client makes a request, the server 
            # includes a Last-Modified header with the timestamp corresponding to when 
            # the resource last changed. The client stores that timestamp. On subsequent 
            # requests, it sends back an "If-Modified-Since" header. The server checks 
            # whether the resource was modified after the timestamp and returns 
            # 304 Not Modified with no body if not. If it was modified, it returns 
            # 200 OK with the new content and an updated Last-Modified. Same benefits 
            # as Etags, except the precision is capped at 1 sec and it does not consider 
            # the case where content is generated identically as it was on the first request.
            ims = request.headers.get("if-modified-since")

            if ims:
                try:
                    ims_dt = datetime.strptime(
                        ims, "%a, %d %b %Y %H:%M:%S GMT"
                    ).replace(tzinfo = timezone.utc)

                    if ims_dt >= last_modified.replace(microsecond = 0):
                        return Response(status_code = status.HTTP_304_NOT_MODIFIED)
                    
                except ValueError:
                    pass

            response.headers["ETag"] = etag
            response.headers["Last-Modified"] = http_date(last_modified)
            response.headers["Cache-Control"] = "public, max-age=300" # 300 seconds = 5 minutes

            if head_only:
                response.headers["Content-Length"] = "0"
                return Response(status_code = status.HTTP_200_OK, headers = dict(response.headers))
            else:
                return cached_value

        # If there is no existing cached tea profiles, proceed as normal.
        # Optimization: We get pagination from limit + offset.
        repo = TeaProfilesRepository(session)
        with sentry_sdk.start_span(op = "db", name = "fetch tea profiles"):
            tea_profiles = repo.list(filters = filters_dict, limit = limit, offset = offset)

        # Cache the tea profiles.
        cache.set(cache_key, tea_profiles)
        cached_entry = cache.get(cache_key)
        cached_entry = cast(CacheEntry, cached_entry)
        cached_value = cached_entry["value"]
        last_modified = cached_entry["timestamp"]

        with sentry_sdk.start_span(op = "etag", name = "generate etag"):
            etag = generate_etag(cached_value)
            
        inm = request.headers.get("if-none-match")

        if inm == etag:
            return Response(status_code = status.HTTP_304_NOT_MODIFIED)

        response.headers["ETag"] = etag
        response.headers["Last-Modified"] = http_date(last_modified)
        response.headers["Cache-Control"] = "public, max-age=300"

        # Verify caching is working.
        # cached = tea_profiles_cache.get(cache_key)
        # if cached is not None:
        #     logger.debug(f"[CACHE HIT] tea list {cache_key}")
        #     return cached

        # logger.debug(f"[CACHE MISS] tea list {cache_key}")

        if head_only:
            response.headers["Content-Length"] = "0"
            return Response(status_code = status.HTTP_200_OK, headers = dict(response.headers))
        else:
            return cached_value

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
@rate_limiter.limit(LOW_RATE_LIMIT)
async def get_tea_profiles(
    request: Request, # required for rate limiter
    response: Response, # required for cache-control headers
    filters: TeaProfileFilters = Depends(get_tea_profile_filters), # type: ignore
    session: Session = Depends(get_session),
    limit: int = 100,
    offset: int = 0
):
    # filters.model_dump(exclude_none = True) returns the Pydantic model as a
    # dict, dropping all fields that have a value of None. 
    #
    # TeaProfileFilters does not belong in TeaProfilesRepository (it's part of the API layer,
    # as it's a Pydantic request schema), so save the dict returned by model_dump here and 
    # pass that along rather than the schema itself. We'll also use filters_dict in the cache.
    filters_dict = filters.model_dump(exclude_none = True)

    return await _get_tea_profiles_common(
        request, response, filters_dict, session, limit, offset, head_only = False
    )

# Optimization: HEAD requests are a cheap way for clients to determine if resources
# have changed without downloading bodies. Clients must explicitly do HEAD calls.
@router.head("/", 
    summary="HEAD version of get_tea_profiles",
    include_in_schema = True, # FastAPI does not autodocument HEADs.
    responses = COMMON_RESPONSES # type: ignore
)
@rate_limiter.limit(LOW_RATE_LIMIT)
async def head_tea_profiles(
    request: Request, 
    response: Response, 
    filters: TeaProfileFilters = Depends(get_tea_profile_filters), # type: ignore
    session: Session = Depends(get_session),
    limit: int = 100,
    offset: int = 0
):
    filters_dict = filters.model_dump(exclude_none = True)

    return await _get_tea_profiles_common(
        request, response, filters_dict, session, limit, offset, head_only = True
    )

####################################################################################

async def _get_tea_profile_common(
    request: Request,
    response: Response,
    tea_profile_id: int, 
    session: Session,
    head_only: bool = False,
):
    '''Gets an entire tea profile for one tea.'''

    with sentry_sdk.start_span(op = "endpoint", name = "tea_profile"):
        sentry_sdk.set_tag("endpoint", "tea_profile")
        sentry_sdk.set_tag("tea_profile_id", tea_profile_id)

        # Try to get tea profile from cache first.
        cache_key = f"tea_profile:{tea_profile_id}"

        with sentry_sdk.start_span(op = "cache", name = "cache lookup"):
            cached_entry = cache.get(cache_key)

        if cached_entry is not None:
            cached_entry = cast(CacheEntry, cached_entry)
            cached_value = cached_entry["value"]
            last_modified = cached_entry["timestamp"]

            # ETag check
            with sentry_sdk.start_span(op = "etag", name = "generate etag"):
                etag = generate_etag(cached_value)

            inm = request.headers.get("if-none-match")

            if inm == etag:
                return Response(status_code = status.HTTP_304_NOT_MODIFIED)

            ims = request.headers.get("if-modified-since")

            # Last-Modified check
            if ims:
                try:
                    ims_dt = datetime.strptime(
                        ims, "%a, %d %b %Y %H:%M:%S GMT"
                    ).replace(tzinfo = timezone.utc)

                    if ims_dt >= last_modified.replace(microsecond = 0):
                        return Response(status_code = status.HTTP_304_NOT_MODIFIED)
                except ValueError:
                    pass

            response.headers["ETag"] = etag
            response.headers["Last-Modified"] = http_date(last_modified)
            response.headers["Cache-Control"] = "public, max-age=300"

            if head_only:
                response.headers["Content-Length"] = "0"
                return Response(status_code = status.HTTP_200_OK, headers = dict(response.headers))
            else:
                return cached_value

        # If there is no existing cached tea profile, proceed as normal.
        repo = TeaProfilesRepository(session)
        with sentry_sdk.start_span(op = "db", name = "fetch tea profile"):
            tea_profile = repo.get_by_id(tea_profile_id)

        # Cache the tea profile.
        cache.set(cache_key, tea_profile)
        cached_entry = cache.get(cache_key)
        cached_entry = cast(CacheEntry, cached_entry)
        cached_value = cached_entry["value"]
        last_modified = cached_entry["timestamp"]

        with sentry_sdk.start_span(op = "etag", name = "generate etag"):
            etag = generate_etag(cached_value)

        inm = request.headers.get("if-none-match")

        if inm == etag:
            return Response(status_code = status.HTTP_304_NOT_MODIFIED)

        response.headers["ETag"] = etag
        response.headers["Last-Modified"] = http_date(last_modified)
        response.headers["Cache-Control"] = "public, max-age=300"

        # Verify caching is working.
        # cached = tea_profile_cache.get(tea_profile_id)
        # if cached is not None:
        #     logger.debug(f"[CACHE HIT] tea profile {tea_profile_id}")
        #     return cached

        # logger.debug(f"[CACHE MISS] tea profile {tea_profile_id}")

        if head_only:
            response.headers["Content-Length"] = "0"
            return Response(status_code = status.HTTP_200_OK, headers = dict(response.headers))
        else:
            return cached_value

@router.get("/{tea_profile_id}", response_model = TeaProfileSchema, 
    responses = COMMON_RESPONSES # type: ignore
)
@rate_limiter.limit(HIGH_RATE_LIMIT)
async def get_tea_profile(
    request: Request, # required for rate limiter
    response: Response, # required for cache-control headers
    tea_profile_id: int, 
    session: Session = Depends(get_session)
):
    return await _get_tea_profile_common(
        request, response, tea_profile_id, session, head_only = False
    )

@router.head("/{tea_profile_id}", 
    summary="HEAD version of get_tea_profile",
    include_in_schema = True, # FastAPI does not autodocument HEADs.
    responses = COMMON_RESPONSES # type: ignore
)
@rate_limiter.limit(HIGH_RATE_LIMIT)
async def head_tea_profile(
    request: Request, 
    response: Response, 
    tea_profile_id: int, 
    session: Session = Depends(get_session),
):
    return await _get_tea_profile_common(
        request, response, tea_profile_id, session, head_only = True
    )