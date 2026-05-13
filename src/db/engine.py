from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import settings

# Create a connection to the PostgreSQL database. engine is an
# instance of the SQLAlchemy engine. SQLAlchemy will use this
# to send queries and receive results. echo = True will print every SQL
# statement to the console.
engine = create_engine(settings.database_url, echo = True)

# Create session factory so sessions can talk to the database.
# SessionLocal is a function call that behaves like a class and
# returns new Session instances. SessionLocal() will start a session
# when we want to add new data, query existing data, or commit changes
# to the database.
SessionLocal = sessionmaker(bind = engine)
