"""
Migration script to add multi-office support:
1. Add display_name column to offices table
2. Create checklist_configs table
"""

from app.core.database import engine, Base
from app.models.models import Office, ChecklistConfig
from sqlalchemy import text

def migrate():
    """Run the migration to add multi-office support."""
    
    # Add display_name column to offices table if it doesn't exist
    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'offices' 
                AND column_name = 'display_name'
            """))
            
            if not result.fetchone():
                print("Adding display_name column to offices table...")
                conn.execute(text("""
                    ALTER TABLE offices 
                    ADD COLUMN display_name VARCHAR(100)
                """))
                conn.commit()
                print("display_name column added successfully")
            else:
                print("display_name column already exists")
                
    except Exception as e:
        print(f"Error adding display_name column: {e}")
    
    # Create checklist_configs table
    try:
        ChecklistConfig.__table__.create(engine, checkfirst=True)
        print("checklist_configs table created (or already exists)")
    except Exception as e:
        print(f"Error creating checklist_configs table: {e}")
    
    print("\nMigration completed successfully!")

if __name__ == "__main__":
    migrate()