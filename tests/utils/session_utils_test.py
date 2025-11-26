from sqlalchemy.orm import Session

from src.utils.session_utils import get_session

def test_get_session_context_manager():

    with get_session() as session:
        assert isinstance(session, Session)