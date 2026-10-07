"""
Create test cases for AI case analysis testing.
Creates one case missing documents and one fully complete case.
"""

import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, get_db
from app.models.models import Office, Staff, Customer, Case, Event, Document
from sqlalchemy.orm import Session

def create_test_cases_for_analysis():
    """
    Create test cases for AI analysis:
    1. Case missing documents
    2. Fully complete case with documents
    """
    
    # Create a new database session
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("Creating test cases for AI analysis...")
        
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
        
        # Get staff member
        staff = db.query(Staff).filter(Staff.email == "admin@test.com").first()
        if not staff:
            print("No staff member found. Please run create_test_staff.py first")
            return
        
        # Create Case 1: Missing documents
        print("\n1. Creating case missing documents...")
        customer1 = Customer(
            office_id=office.id,
            full_name="John Smith",
            phone="555-1001",
            email="john.smith@test.com",
            address="100 Missing Doc Street"
        )
        db.add(customer1)
        db.flush()
        
        case1 = Case(
            office_id=office.id,
            customer_id=customer1.id,
            service_type="New Registration",
            status="pending",
            vehicle_number="MH01AB1234",
            notes="Test case missing documents for AI analysis"
        )
        db.add(case1)
        db.flush()
        
        # Create events for case 1 (no documents)
        event1_created = Event(
            case_id=case1.id,
            office_id=office.id,
            event_type="case_created",
            description="Case created for New Registration",
            created_by=staff.email,
            created_at=datetime.now() - timedelta(days=5)
        )
        db.add(event1_created)
        
        event1_status = Event(
            case_id=case1.id,
            office_id=office.id,
            event_type="status_changed",
            description="Status changed to pending",
            created_by=staff.email,
            created_at=datetime.now() - timedelta(days=4)
        )
        db.add(event1_status)
        
        print(f"Created case {case1.id} (missing documents): John Smith - New Registration")
        
        # Create Case 2: Fully complete with documents
        print("\n2. Creating fully complete case...")
        customer2 = Customer(
            office_id=office.id,
            full_name="Jane Doe",
            phone="555-1002",
            email="jane.doe@test.com",
            address="200 Complete Doc Avenue"
        )
        db.add(customer2)
        db.flush()
        
        case2 = Case(
            office_id=office.id,
            customer_id=customer2.id,
            service_type="Transfer",
            status="completed",
            vehicle_number="MH02CD5678",
            notes="Test complete case for AI analysis"
        )
        db.add(case2)
        db.flush()
        
        # Create events for case 2
        event2_created = Event(
            case_id=case2.id,
            office_id=office.id,
            event_type="case_created",
            description="Case created for Transfer",
            created_by=staff.email,
            created_at=datetime.now() - timedelta(days=10)
        )
        db.add(event2_created)
        
        # Add documents to case 2
        doc1 = Document(
            case_id=case2.id,
            office_id=office.id,
            document_type="ID Proof",
            file_name="id_proof_jane_doe.pdf",
            r2_object_key="test/id_proof_jane_doe.pdf",
            uploaded_at=datetime.now() - timedelta(days=9)
        )
        db.add(doc1)
        
        doc2 = Document(
            case_id=case2.id,
            office_id=office.id,
            document_type="Address Proof",
            file_name="address_proof_jane_doe.pdf",
            r2_object_key="test/address_proof_jane_doe.pdf",
            uploaded_at=datetime.now() - timedelta(days=8)
        )
        db.add(doc2)
        
        doc3 = Document(
            case_id=case2.id,
            office_id=office.id,
            document_type="Vehicle RC",
            file_name="vehicle_rc_jane_doe.pdf",
            r2_object_key="test/vehicle_rc_jane_doe.pdf",
            uploaded_at=datetime.now() - timedelta(days=7)
        )
        db.add(doc3)
        
        # Document upload events
        event2_doc1 = Event(
            case_id=case2.id,
            office_id=office.id,
            event_type="document_uploaded",
            description="Document uploaded: ID Proof (id_proof_jane_doe.pdf)",
            created_by=staff.email,
            created_at=datetime.now() - timedelta(days=9)
        )
        db.add(event2_doc1)
        
        event2_doc2 = Event(
            case_id=case2.id,
            office_id=office.id,
            event_type="document_uploaded",
            description="Document uploaded: Address Proof (address_proof_jane_doe.pdf)",
            created_by=staff.email,
            created_at=datetime.now() - timedelta(days=8)
        )
        db.add(event2_doc2)
        
        event2_doc3 = Event(
            case_id=case2.id,
            office_id=office.id,
            event_type="document_uploaded",
            description="Document uploaded: Vehicle RC (vehicle_rc_jane_doe.pdf)",
            created_by=staff.email,
            created_at=datetime.now() - timedelta(days=7)
        )
        db.add(event2_doc3)
        
        # Completion event
        event2_completed = Event(
            case_id=case2.id,
            office_id=office.id,
            event_type="case_completed",
            description="Case completed for Transfer",
            created_by=staff.email,
            created_at=datetime.now() - timedelta(days=1)
        )
        db.add(event2_completed)
        
        print(f"Created case {case2.id} (complete): Jane Doe - Transfer with 3 documents")
        
        # Commit all changes
        db.commit()
        print("\nTest cases created successfully!")
        print(f"Case {case1.id}: Missing documents - {customer1.full_name}")
        print(f"Case {case2.id}: Complete with documents - {customer2.full_name}")
        print("\nUse these case IDs to test the AI analysis feature:")
        print(f"- Missing documents: http://localhost:8000/case/{case1.id}")
        print(f"- Complete case: http://localhost:8000/case/{case2.id}")
        
    except Exception as e:
        db.rollback()
        print(f"Error creating test cases: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_cases_for_analysis()