"""
Database reset script.
This drops all tables and recreates them with the current schema.
WARNING: This will delete all existing data!
"""

from app.core.database import engine, Base
from sqlalchemy import text

def drop_all_tables():
    """Drop all tables in the database."""
    print("Dropping all tables...")
    with engine.connect() as conn:
        # Drop all tables in reverse order of dependencies
        conn.execute(text("DROP TABLE IF EXISTS events CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS documents CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS cases CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS customers CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS staff CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS offices CASCADE"))
        conn.commit()
        print("All tables dropped!")

def create_tables():
    """Create all tables in the database."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    drop_all_tables()
    create_tables()
    print("\nDatabase reset complete!")