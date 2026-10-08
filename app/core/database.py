import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database connection URL from environment variable
# Supports both full DATABASE_URL and legacy DB_* variables
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback to legacy DB_* variables for backward compatibility
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "rto_autopilot")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Check if using SQLite for local development
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
if USE_SQLITE:
    DATABASE_URL = "sqlite:///./test.db"
    print("Using SQLite database for local development")

# Create the SQLAlchemy engine
# This engine manages the database connections
# Add pool settings for better resilience
if USE_SQLITE:
    # SQLite doesn't support connection pooling
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}  # Needed for SQLite
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Check connections before using them
        pool_recycle=3600,   # Recycle connections after 1 hour
        pool_size=5,
        max_overflow=10
    )

# Create a SessionLocal class
# This will be used to create database sessions for interacting with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class
# All your database models will inherit from this Base class
Base = declarative_base()

# Dependency function to get database session
# This will be used in FastAPI route handlers to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
