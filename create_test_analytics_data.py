"""
Test Data Generator for Analytics
This script creates sample test data to demonstrate the analytics functionality.
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, get_db
from app.models.models import Office, Staff, Customer, Case, Event
from sqlalchemy.orm import Session

def create_test_analytics_data():
    """
    Create test data for analytics testing including:
    - Cases with different completion times
    - Document requested/received events
    - Staff performance data
    """
    
    # Create a new database session
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("Creating test analytics data...")
        
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
        
        # Get or create staff members
        staff_emails = ["admin@test.com", "staff1@test.com", "staff2@test.com"]
        staff_members = []
        
        for email in staff_emails:
            staff = db.query(Staff).filter(Staff.email == email).first()
            if not staff:
                staff = Staff(
                    office_id=office.id,
                    email=email,
                    password_hash="hashed_password_here",  # In production, this would be properly hashed
                    full_name=email.split('@')[0].replace('.', ' ').title(),
                    role="admin" if "admin" in email else "staff",
                    is_active=1
                )
                db.add(staff)
                db.flush()
                print(f"Created staff: {staff.full_name}")
            staff_members.append(staff)
        
        # Service types to test
        service_types = ["New Registration", "Transfer", "Renewal", "Address Change", "Name Change"]
        
        # Document types to test
        document_types = ["ID Proof", "Address Proof", "Vehicle RC", "Insurance", "PUC Certificate"]
        
        # Create customers and cases with events
        print("Creating test cases and events...")
        
        for i in range(20):  # Create 20 test cases
            # Create customer
            customer = Customer(
                office_id=office.id,
                full_name=f"Test Customer {i+1}",
                phone=f"555-{1000+i}",
                email=f"customer{i+1}@test.com",
                address=f"{i+1} Test Street"
            )
            db.add(customer)
            db.flush()
            
            # Create case
            service_type = random.choice(service_types)
            case = Case(
                office_id=office.id,
                customer_id=customer.id,
                service_type=service_type,
                status="completed",
                vehicle_number=f"MH{random.randint(10,99)}{random.randint(1000,9999)}",
                notes=f"Test case {i+1}"
            )
            db.add(case)
            db.flush()
            
            # Random completion time between 1-7 days
            completion_hours = random.randint(24, 168)  # 1-7 days in hours
            
            # Create events with timestamps
            created_at = datetime.now() - timedelta(days=random.randint(1, 30))
            completed_at = created_at + timedelta(hours=completion_hours)
            
            # Case created event
            event_created = Event(
                case_id=case.id,
                office_id=office.id,
                event_type="case_created",
                description=f"Case created for {service_type}",
                created_by=random.choice(staff_members).email,
                created_at=created_at
            )
            db.add(event_created)
            
            # Document requested/received events (70% chance)
            if random.random() > 0.3:
                doc_type = random.choice(document_types)
                doc_requested_at = created_at + timedelta(hours=random.randint(1, 12))
                doc_received_at = doc_requested_at + timedelta(hours=random.randint(1, 48))
                
                event_doc_requested = Event(
                    case_id=case.id,
                    office_id=office.id,
                    event_type="document_requested",
                    description=f"Document requested: {doc_type}",
                    created_by=random.choice(staff_members).email,
                    created_at=doc_requested_at
                )
                db.add(event_doc_requested)
                
                event_doc_received = Event(
                    case_id=case.id,
                    office_id=office.id,
                    event_type="document_received",
                    description=f"Document received: {doc_type}",
                    created_by=random.choice(staff_members).email,
                    created_at=doc_received_at
                )
                db.add(event_doc_received)
            
            # Case completed event
            event_completed = Event(
                case_id=case.id,
                office_id=office.id,
                event_type="case_completed",
                description=f"Case completed for {service_type}",
                created_by=random.choice(staff_members).email,
                created_at=completed_at
            )
            db.add(event_completed)
            
            print(f"Created case {case.id}: {service_type} (completed in {completion_hours} hours)")
        
        # Commit all changes
        db.commit()
        print("\nTest analytics data created successfully!")
        print(f"Created {len(staff_members)} staff members")
        print(f"Created 20 test cases with events")
        print(f"Staff emails: {', '.join([s.email for s in staff_members])}")
        
    except Exception as e:
        db.rollback()
        print(f"\nError creating test data: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_analytics_data()