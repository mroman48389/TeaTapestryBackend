# Layer 3 (Database/SQLAlchemy/bottomost layer): This is where error handling starts. We
# catch raw SQLAlchemy errors and convert them into the domain errors that layer 2 deals
# with. This layer ensures raw SQL errors don't reach layer 1.

from __future__ import annotations
from sqlalchemy import text

from src.db.engine import engine

# A repository is a class tasked with talking to a database and returning domain objects. It
# should be the only place on the backend that knows how to query the DB, insert/update/delete,
# translate SQLAlchemy errors, and manage transactions. 
# 
# It's a class rather than a set of functions because it needs to work on a database session. 
# Without it, we'd need to pass a session into each function of said set. It's useful for testing.
class HealthDBTeaProfilesRepository:

    def check_connection(self) -> bool:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))

            return True
        
        except Exception:
            
            return False