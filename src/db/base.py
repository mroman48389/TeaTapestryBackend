from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from dotenv import load_dotenv
import os
import urllib.parse

# Load variables from .env into environment
load_dotenv()

# Prefer DATABASE_URL if set (e.g. in CI)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fall back to building Postgres URL from individual parts
    user = os.getenv("DB_USER")
    # In case our password has special character in our .env file, we need to
    # encode them to prevent breaks.(Characters like @, !, #, etc.)
    password_raw = os.getenv("DB_PASS") or ""
    password = urllib.parse.quote_plus(password_raw)
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    db   = os.getenv("DB_NAME")

    DATABASE_URL = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

# Create a connection to the PostgreSQL database. engine is an
# instance of the SQLAlchemy engine. SQLAlchemy will use this
# to send queries and receive results. echo = True will print every SQL
# statement to the console.
engine = create_engine(DATABASE_URL, echo = True)

# Create session factory so sessions can talk to the database.
# SessionLocal is a function call that behaves like a class and
# returns new Session instances. SessionLocal() will start a session
# when we want to add new data, query existing data, or commit changes
# to the database.
SessionLocal = sessionmaker(bind = engine)

# Base class for all models. All tables will inherit from this. It
# registers models so SQLAlchemy knows how to map them to actual
# database tables.
class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base class."""
    pass