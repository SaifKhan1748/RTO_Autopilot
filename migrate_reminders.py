"""
Migration script to add the pending_reminders table to the database.
Run this script to create the new table for the reminder system.
"""

from app.core.database import engine, Base
from app.models.models import PendingReminder

def migrate():
    """Create the pending_reminders table if it doesn't exist."""
    print("Creating pending_reminders table...")
    
    # Create the table
    PendingReminder.__table__.create(engine, checkfirst=True)
    
    print("Migration completed successfully!")
    print("The pending_reminders table has been added to your database.")

if __name__ == "__main__":
    migrate()