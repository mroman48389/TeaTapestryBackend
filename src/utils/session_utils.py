from contextlib import contextmanager

from src.db.base import SessionLocal

# Note that there is a built-in SQLAlchemy context manager, but 
# this one lets us add custom code.
@contextmanager
def get_session():
    # Open a new SQLAlchemy session so we can talk to the database.
    session = SessionLocal()

    try:
        # Hand over control of the session to the calling code.
        yield session

    finally:
        # Make sure session is closed, even if it crashes.
        session.close()