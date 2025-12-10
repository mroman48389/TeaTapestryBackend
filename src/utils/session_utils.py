from contextlib import contextmanager

from src.db.base import SessionLocal

# Generators are functions that yield control back to their calling function at
# some point in the code. So when this is called, it opens a new SQLAlchemy
# session and yields the session value to the calling function. 
# The caller performs some operation with it while the generator is paused. 
# When the caller is done, control returns to the generator. In this case, 
# the generator closes the session that was used by the caller.
def _get_session_generator():
    """Private generator function that opens and closes SQLAlchemy sessions."""
    # Open a new SQLAlchemy session so we can talk to the database.
    session = SessionLocal()

    try:
        # Hand over control of the session to the calling code.
        yield session

    finally:
        # Make sure session is closed, even if it crashes.
        session.close()

# Note that there is a built-in SQLAlchemy context manager, but
# this one lets us add custom code. Using this as "with get_session()"
# will return a session.
@contextmanager
def get_session_cm():
    """Context manager version for scripts, migrations, etc."""
    yield from _get_session_generator()

# Since this is NOT a context manager, this version CANNOT be used via
# the "with" statement and returns a generator rather than a session!
def get_session():
    """Standard version usable with FastAPI's Depends."""
    yield from _get_session_generator()