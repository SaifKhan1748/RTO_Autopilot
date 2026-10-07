"""
Migration script to add password reset functionality.
Adds failed_login_attempts, locked_until fields to Staff table
and creates the PasswordReset table.
"""
from sqlalchemy import text
from app.core.database import engine, Base
from app.models.models import Staff, PasswordReset

def migrate():
    """Run the migration."""
    with engine.connect() as conn:
        # Add new columns to Staff table if they don't exist
        try:
            conn.execute(text("ALTER TABLE staff ADD COLUMN failed_login_attempts INTEGER DEFAULT 0"))
            print("Added failed_login_attempts column to staff table")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("failed_login_attempts column already exists")
            else:
                print(f"Error adding failed_login_attempts: {e}")
        
        try:
            conn.execute(text("ALTER TABLE staff ADD COLUMN locked_until TIMESTAMP"))
            print("Added locked_until column to staff table")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("locked_until column already exists")
            else:
                print(f"Error adding locked_until: {e}")
        
        # Create PasswordReset table
        try:
            PasswordReset.__table__.create(engine, checkfirst=True)
            print("Created password_resets table")
        except Exception as e:
            print(f"Error creating password_resets table: {e}")
        
        conn.commit()
        print("Migration completed successfully")

if __name__ == "__main__":
    migrate()
