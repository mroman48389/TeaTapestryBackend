from sqlalchemy.orm import Session

from src.utils.session_utils import get_session_cm, get_session

def test_get_session_cm():

    with get_session_cm() as session:
        assert isinstance(session, Session)

def test_get_session():
    # Get the session generator.
    generator = get_session()

    # Advance to when the session is yielded
    session = next(generator)
    
    # Now we can ensure the session is a Session.
    assert isinstance(session, Session)

    # Close the session (advances to the finally of the generator).
    generator.close()