"""
Enable pgvector extension in PostgreSQL database.
Run this script once to enable the pgvector extension for vector similarity search.
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "rto_autopilot")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Construct the database connection URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def enable_pgvector_extension():
    """Enable the pgvector extension in the database."""
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            # Enable pgvector extension
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.commit()
            
            print("pgvector extension enabled successfully!")
            
            # Verify the extension is installed
            result = connection.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
            if result.fetchone():
                print("pgvector extension is active and ready to use.")
            else:
                print("Failed to verify pgvector extension.")
                
    except Exception as e:
        print(f"Error enabling pgvector extension: {e}")
        raise

if __name__ == "__main__":
    enable_pgvector_extension()