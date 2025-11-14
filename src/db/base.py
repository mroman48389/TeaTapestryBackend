from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from dotenv import load_dotenv
import os

# Load variables from .env into environment
load_dotenv()
DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# Create a connection to the PostgreSQL database. engine is an
# instance of the SQLAlchemy engine. SQLAlchemy will use this
# to send queries and receive results. echo = True will print every SQL
# statement to the console.
engine = create_engine(DATABASE_URL, echo=True)

# Create session factory so sessions can talk to the database.
# SessionLocal is a function call that behaves like a class and
# returns new Session instances. SessionLocal() will start a session
# when we want to add new data, query existing data, or commit changes
# to the database.
SessionLocal = sessionmaker(bind=engine)

# Base class for all models. All tables will inherit from this. It
# registers models so SQLAlchemy knows how to map them to actual
# database tables.
Base = declarative_base()
