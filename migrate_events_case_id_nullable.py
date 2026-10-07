"""
Database Migration: Make events.case_id column nullable.
This allows office-level and administrative audit events (like customer deletion)
to be recorded when there is no associated case.
"""

import sys
import os
from pathlib import Path
from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine

def migrate():
    print("Starting migration: Make events.case_id nullable...")
    
    with engine.connect() as conn:
        # Check current column nullability
        inspector = inspect(engine)
        columns = {col['name']: col for col in inspector.get_columns('events')}
        
        if 'case_id' in columns:
            is_nullable = columns['case_id']['nullable']
            print(f"Current events.case_id nullable status: {is_nullable}")
            
            if not is_nullable:
                print("Executing: ALTER TABLE events ALTER COLUMN case_id DROP NOT NULL;")
                conn.execute(text("ALTER TABLE events ALTER COLUMN case_id DROP NOT NULL;"))
                conn.commit()
                print("Migration successful! events.case_id is now nullable.")
            else:
                print("events.case_id is already nullable. No change needed.")
        else:
            print("Error: events table does not have a case_id column.")

if __name__ == "__main__":
    migrate()
