from datetime import timedelta, datetime, timezone


def just_expired_td(window: timedelta) -> timedelta:
    '''
        Returns a timedelta that has just missed the 
        provided window by 1 second.
    '''
    return window + timedelta(seconds = 1)


def just_valid_td(window: timedelta) -> timedelta:
    '''
        Returns a timedelta that is just within the 
        provided window by 1 second.
    '''
    return window - timedelta(seconds = 1)


def before_now_dt(td: timedelta) -> datetime:
    '''
        Returns a timezone-aware UTC datetime representing 
        how long ago an event occurred before "now()".
    '''
    return datetime.now(timezone.utc) - td


def after_now_dt(td: timedelta) -> datetime:
    '''
        Returns a timezone-aware UTC datetime representing 
        how long ago an event occurred after "now()".
    '''
    return datetime.now(timezone.utc) + td


def is_older_than(dt: datetime, window: timedelta, include_same_age: bool = False) -> bool:
    '''
        Returns True if the provided dt occurred more than
        "window" ago relative to now(), UTC. 
        
        If include_same_age is True, then a dt exactly "window" age counts as older.
    '''
    # Normalize naive datetimes (SQLite strips timezone info in testing)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo = timezone.utc)

    now = datetime.now(timezone.utc)
    age = now - dt

    return (age >= window) if include_same_age else (age > window)


def is_younger_than(dt: datetime, window: timedelta, include_same_age: bool = False) -> bool:
    '''
        Returns True if the provided dt occurred less than 
        "window" ago relative to now(), UTC.
        
        If include_same_age is True, then a dt exactly "window" ago counts as younger.
    '''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo = timezone.utc)

    now = datetime.now(timezone.utc)
    age = now - dt

    return (age <= window) if include_same_age else (age < window)


def is_in_past(dt: datetime) -> bool:
    '''
        Returns True if the provided dt occurs before now(), UTC.
    '''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo = timezone.utc)

    now = datetime.now(timezone.utc)

    return dt < now


def is_in_future(dt: datetime) -> bool:
    '''
        Returns True if the provided dt occurs after now(), UTC.
    '''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo = timezone.utc)

    now = datetime.now(timezone.utc)

    return dt > now


