from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Using SQLite for the hackathon, but this architecture allows instant 
# swapping to PostgreSQL/MySQL for enterprise production.
SQLALCHEMY_DATABASE_URL = "sqlite:///./event_media.db"

# connect_args is required for SQLite to prevent multi-threading errors
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()