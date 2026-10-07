"""
Database initialization script.
This creates all tables in the database and adds sample data for testing.
Run this once to set up your database.
"""

from app.core.database import engine, Base, SessionLocal
from app.models.models import Office, Staff, Customer, Case
import bcrypt

def create_tables():
    """Create all tables in the database."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

def add_sample_data():
    """Add sample data for testing."""
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(Office).first():
            print("Sample data already exists. Skipping...")
            return
        
        print("Adding sample data...")
        
        # Create a sample office
        office = Office(
            name="Downtown RTO Office",
            code="RTO-001",
            address="123 Main Street, Downtown",
            phone="555-1234"
        )
        db.add(office)
        db.flush()  # Get the office ID
        
        # Create a sample staff member
        # Password is "password" - you should change this in production!
        hashed_password = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        staff = Staff(
            office_id=office.id,
            email="admin@rto.com",
            password_hash=hashed_password,
            full_name="Admin User",
            role="admin",
            is_active=1
        )
        db.add(staff)
        db.flush()
        
        # Create sample customers
        customer1 = Customer(
            office_id=office.id,
            full_name="John Smith",
            phone="555-1111",
            email="john@example.com",
            address="456 Oak Avenue"
        )
        customer2 = Customer(
            office_id=office.id,
            full_name="Jane Doe",
            phone="555-2222",
            email="jane@example.com",
            address="789 Pine Street"
        )
        db.add(customer1)
        db.add(customer2)
        db.flush()
        
        # Create sample cases
        case1 = Case(
            office_id=office.id,
            customer_id=customer1.id,
            service_type="New Registration",
            status="pending",
            vehicle_number="ABC-1234",
            notes="First-time vehicle registration"
        )
        case2 = Case(
            office_id=office.id,
            customer_id=customer2.id,
            service_type="Transfer",
            status="in_progress",
            vehicle_number="XYZ-5678",
            notes="Vehicle ownership transfer"
        )
        case3 = Case(
            office_id=office.id,
            customer_id=customer1.id,
            service_type="Renewal",
            status="completed",
            vehicle_number="DEF-9012",
            notes="Annual registration renewal"
        )
        db.add(case1)
        db.add(case2)
        db.add(case3)
        
        db.commit()
        print("Sample data added successfully!")
        print("\nSample login credentials:")
        print("Email: admin@rto.com")
        print("Password: password")
        
    except Exception as e:
        db.rollback()
        print(f"Error adding sample data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_tables()
    add_sample_data()
    print("\nDatabase initialization complete!")
