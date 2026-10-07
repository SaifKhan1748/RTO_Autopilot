"""
Create test staff member for analytics testing
"""

import sys
import os
import bcrypt

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, get_db
from app.models.models import Office, Staff
from sqlalchemy.orm import Session

def create_test_staff():
    """
    Create a test staff member with known credentials for testing.
    """
    
    # Create a new database session
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("Creating test staff member...")
        
        # Get or create office
        office = db.query(Office).first()
        if not office:
            office = Office(
                name="Test Office",
                code="TEST001",
                address="123 Test Street",
                phone="555-1234"
            )
            db.add(office)
            db.flush()
            print(f"Created office: {office.name}")
        
        # Create test staff member
        test_email = "admin@test.com"
        test_password = "admin123"
        
        # Check if staff already exists
        existing_staff = db.query(Staff).filter(Staff.email == test_email).first()
        if existing_staff:
            print(f"Staff member {test_email} already exists")
            print(f"Email: {test_email}")
            print(f"Password: {test_password}")
            return
        
        # Hash the password
        password_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create staff member
        staff = Staff(
            office_id=office.id,
            email=test_email,
            password_hash=password_hash,
            full_name="Test Admin",
            role="admin",
            is_active=1
        )
        db.add(staff)
        db.commit()
        
        print("Test staff member created successfully!")
        print(f"Email: {test_email}")
        print(f"Password: {test_password}")
        print("Use these credentials to log in and test the analytics")
        
    except Exception as e:
        db.rollback()
        print(f"Error creating test staff: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_staff()