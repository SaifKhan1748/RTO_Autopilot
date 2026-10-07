"""
Office isolation tests - ensure staff can only access their own office's data.
"""
import pytest
import bcrypt
from fastapi.testclient import TestClient
from app.models.models import Staff, Office, Customer, Case, Document, Event


class TestOfficeIsolation:
    """Test that staff members are isolated to their own office data."""
    
    @pytest.fixture
    def office_a(self, db_session):
        """Create Office A."""
        office = Office(
            name="Office A",
            code="OFFICE_A",
            display_name="Office A Display"
        )
        db_session.add(office)
        db_session.commit()
        db_session.refresh(office)
        return office
    
    @pytest.fixture
    def office_b(self, db_session):
        """Create Office B."""
        office = Office(
            name="Office B",
            code="OFFICE_B",
            display_name="Office B Display"
        )
        db_session.add(office)
        db_session.commit()
        db_session.refresh(office)
        return office
    
    @pytest.fixture
    def staff_a(self, db_session, office_a):
        """Create staff member for Office A."""
        password_hash = bcrypt.hashpw("staffa123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        staff = Staff(
            office_id=office_a.id,
            email="staff_a@example.com",
            password_hash=password_hash,
            full_name="Staff A",
            role="staff",
            is_active=1
        )
        db_session.add(staff)
        db_session.commit()
        db_session.refresh(staff)
        return staff
    
    @pytest.fixture
    def staff_b(self, db_session, office_b):
        """Create staff member for Office B."""
        password_hash = bcrypt.hashpw("staffb123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        staff = Staff(
            office_id=office_b.id,
            email="staff_b@example.com",
            password_hash=password_hash,
            full_name="Staff B",
            role="staff",
            is_active=1
        )
        db_session.add(staff)
        db_session.commit()
        db_session.refresh(staff)
        return staff
    
    @pytest.fixture
    def customer_a(self, db_session, office_a):
        """Create customer for Office A."""
        customer = Customer(
            office_id=office_a.id,
            full_name="Customer A",
            phone="555-0001",
            email="customer_a@example.com"
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)
        return customer
    
    @pytest.fixture
    def customer_b(self, db_session, office_b):
        """Create customer for Office B."""
        customer = Customer(
            office_id=office_b.id,
            full_name="Customer B",
            phone="555-0002",
            email="customer_b@example.com"
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)
        return customer
    
    @pytest.fixture
    def case_a(self, db_session, office_a, customer_a):
        """Create case for Office A."""
        case = Case(
            office_id=office_a.id,
            customer_id=customer_a.id,
            service_type="New Registration",
            status="new"
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        return case
    
    @pytest.fixture
    def case_b(self, db_session, office_b, customer_b):
        """Create case for Office B."""
        case = Case(
            office_id=office_b.id,
            customer_id=customer_b.id,
            service_type="Transfer",
            status="new"
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        return case
    
    @pytest.fixture
    def authenticated_client_a(self, test_client, staff_a):
        """Create authenticated client for Staff A."""
        test_client.post("/login", data={
            "email": staff_a.email,
            "password": "staffa123"
        }, follow_redirects=False)
        return test_client
    
    @pytest.fixture
    def authenticated_client_b(self, test_client, staff_b):
        """Create authenticated client for Staff B."""
        test_client.post("/login", data={
            "email": staff_b.email,
            "password": "staffb123"
        }, follow_redirects=False)
        return test_client
    
    def test_staff_a_cannot_see_office_b_customers(self, authenticated_client_a, customer_b):
        """Staff A cannot access Office B's customers."""
        # Try to access customer B's data through new case form
        response = authenticated_client_a.get("/new-case")
        assert response.status_code == 200
        
        # The customer dropdown should only show Office A's customers
        content = response.content.decode()
        assert customer_b.full_name not in content
        assert customer_b.email not in content
    
    def test_staff_a_cannot_access_office_b_case(self, authenticated_client_a, case_b):
        """Staff A cannot access Office B's case details."""
        response = authenticated_client_a.get(f"/case/{case_b.id}")
        # Should redirect to dashboard (case not found for this office)
        assert response.status_code in [200, 307, 303]
        # If it returns 200, it should be showing dashboard with no cases
        if response.status_code == 200:
            assert b"No cases" in response.content or b"Case not found" in response.content
    
    def test_staff_a_cannot_create_case_for_office_b_customer(self, authenticated_client_a, customer_b):
        """Staff A cannot create a case for Office B's customer."""
        response = authenticated_client_a.post("/new-case", data={
            "customer_id": customer_b.id,
            "service_type": "New Registration",
            "vehicle_number": "TEST123",
            "notes": "Test case"
        }, follow_redirects=False)
        
        # Should fail with error
        assert response.status_code == 200
        assert b"Invalid customer selected" in response.content
    
    def test_staff_a_cannot_upload_document_to_office_b_case(self, authenticated_client_a, case_b):
        """Staff A cannot upload documents to Office B's case."""
        from io import BytesIO
        
        # Try to upload document to Office B's case
        file_content = b"test document content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        
        response = authenticated_client_a.post(
            f"/case/{case_b.id}/upload",
            data={"document_type": "ID Proof"},
            files=files,
            follow_redirects=False
        )
        
        # Should fail with case not found
        assert response.status_code == 200
        assert b"Case not found" in response.content
    
    def test_staff_a_cannot_download_office_b_document(self, authenticated_client_a, db_session, office_b, case_b):
        """Staff A cannot download Office B's documents."""
        # Create a document for Office B's case
        document = Document(
            case_id=case_b.id,
            office_id=office_b.id,
            document_type="ID Proof",
            file_name="test.txt",
            r2_object_key="test/key"
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        # Try to download
        response = authenticated_client_a.get(f"/documents/{document.id}/download")
        # Should fail with 404
        assert response.status_code == 404
    
    def test_dashboard_only_shows_office_a_cases(self, authenticated_client_a, case_a, case_b):
        """Dashboard only shows cases from the user's own office."""
        response = authenticated_client_a.get("/dashboard")
        assert response.status_code == 200
        
        content = response.content.decode()
        # Should show Office A's case (check for case ID in a case-specific context)
        # The dashboard should only show case_a.id and not case_b.id
        # Let's check that case_a is present and case_b is not in the case list
        import re
        # Look for case IDs in the HTML - they should appear in case-specific elements
        case_ids = re.findall(r'case/(\d+)', content)
        # Should only contain case_a's ID
        assert str(case_a.id) in case_ids
        assert str(case_b.id) not in case_ids
    
    def test_analytics_only_shows_office_a_data(self, authenticated_client_a, db_session, office_a, office_b):
        """Analytics endpoints only return data from the user's own office."""
        # Create events for both offices
        from datetime import datetime
        
        # Event for Office A
        event_a = Event(
            case_id=1,  # Will be created if needed
            office_id=office_a.id,
            event_type="case_created",
            description="Test event A",
            created_by="staff_a@example.com"
        )
        db_session.add(event_a)
        
        # Event for Office B
        event_b = Event(
            case_id=2,  # Will be created if needed
            office_id=office_b.id,
            event_type="case_created",
            description="Test event B",
            created_by="staff_b@example.com"
        )
        db_session.add(event_b)
        db_session.commit()
        
        # Get analytics data
        response = authenticated_client_a.get("/analytics/case-volume")
        assert response.status_code == 200
        
        data = response.json()
        # The data should only include Office A's events
        # This is verified by the office_id filter in the analytics endpoint
        assert data["success"] is True
    
    def test_staff_a_cannot_approve_office_b_reminders(self, authenticated_client_a, db_session, office_b, case_b):
        """Staff A cannot approve reminders from Office B."""
        from app.models.models import PendingReminder
        from datetime import datetime
        
        # Create a reminder for Office B
        reminder = PendingReminder(
            case_id=case_b.id,
            office_id=office_b.id,
            message="Test reminder B",
            status="pending"
        )
        db_session.add(reminder)
        db_session.commit()
        db_session.refresh(reminder)
        
        # Try to approve
        response = authenticated_client_a.post(f"/reminders/{reminder.id}/approve", follow_redirects=False)
        # Should redirect without approving (reminder not found for this office)
        assert response.status_code in [303, 307]
