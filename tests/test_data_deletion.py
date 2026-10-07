"""
Data deletion tests - ensure admin-only data deletion works correctly and removes all data.
"""
import pytest
from app.models.models import Customer, Case, Document, Event, PendingReminder, Staff


class TestDataDeletion:
    """Test admin-only data deletion functionality."""
    
    @pytest.fixture
    def admin_staff(self, db_session, test_office):
        """Create an admin staff member."""
        import bcrypt
        password_hash = bcrypt.hashpw("adminpassword123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        admin = db_session.query(Staff).filter(Staff.email == "admin@example.com").first()
        if not admin:
            admin = Staff(
                office_id=test_office.id,
                email="admin@example.com",
                password_hash=password_hash,
                full_name="Admin User",
                role="admin",
                is_active=1
            )
            db_session.add(admin)
            db_session.commit()
            db_session.refresh(admin)
        return admin
    
    @pytest.fixture
    def regular_staff(self, db_session, test_office):
        """Create a regular staff member."""
        import bcrypt
        password_hash = bcrypt.hashpw("staffpassword123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        staff = Staff(
            office_id=test_office.id,
            email="staff@example.com",
            password_hash=password_hash,
            full_name="Regular Staff",
            role="staff",
            is_active=1
        )
        db_session.add(staff)
        db_session.commit()
        db_session.refresh(staff)
        return staff
    
    @pytest.fixture
    def customer_with_data(self, db_session, test_office):
        """Create a customer with cases, documents, and events."""
        customer = Customer(
            office_id=test_office.id,
            full_name="Test Customer",
            phone="555-9999",
            email="test@example.com"
        )
        db_session.add(customer)
        db_session.flush()
        
        # Create a case
        case = Case(
            office_id=test_office.id,
            customer_id=customer.id,
            service_type="New Registration",
            status="new"
        )
        db_session.add(case)
        db_session.flush()
        
        # Create a document
        document = Document(
            case_id=case.id,
            office_id=test_office.id,
            document_type="ID Proof",
            file_name="test.pdf",
            r2_object_key="test/key"
        )
        db_session.add(document)
        db_session.flush()
        
        # Create an event
        event = Event(
            case_id=case.id,
            office_id=test_office.id,
            event_type="case_created",
            description="Test event",
            created_by="admin@example.com"
        )
        db_session.add(event)
        
        # Create a reminder
        reminder = PendingReminder(
            case_id=case.id,
            office_id=test_office.id,
            message="Test reminder",
            status="pending"
        )
        db_session.add(reminder)
        
        db_session.commit()
        db_session.refresh(customer)
        
        return customer
    
    @pytest.fixture
    def authenticated_admin_client(self, test_client, admin_staff):
        """Create authenticated admin client."""
        test_client.post("/login", data={
            "email": admin_staff.email,
            "password": "adminpassword123"
        }, follow_redirects=False)
        return test_client
    
    @pytest.fixture
    def authenticated_staff_client(self, test_client, regular_staff):
        """Create authenticated regular staff client."""
        test_client.post("/login", data={
            "email": regular_staff.email,
            "password": "staffpassword123"
        }, follow_redirects=False)
        return test_client
    
    def test_admin_can_access_data_deletion_page(self, authenticated_admin_client):
        """Admin can access data deletion page."""
        response = authenticated_admin_client.get("/admin/data-deletion")
        assert response.status_code == 200
        assert b"Data Deletion" in response.content
    
    def test_regular_staff_cannot_access_data_deletion_page(self, authenticated_staff_client):
        """Regular staff cannot access data deletion page."""
        response = authenticated_staff_client.get("/admin/data-deletion")
        assert response.status_code == 200
        # Should be redirected to dashboard - check that it's dashboard content
        assert b"Dashboard" in response.content or b"Office Cases" in response.content
    
    def test_data_deletion_requires_confirmation(self, authenticated_admin_client, customer_with_data, db_session):
        """Data deletion requires 'delete' confirmation."""
        response = authenticated_admin_client.post("/admin/delete-customer", data={
            "customer_id": customer_with_data.id,
            "confirmation": "wrong"  # Wrong confirmation
        }, follow_redirects=False)
        
        assert response.status_code == 200
        # Check if we get an error or the confirmation page again
        content = response.content.decode().lower()
        assert "must type" in content or "confirm" in content or "error" in content
        
        # Verify customer still exists
        customer = db_session.query(Customer).filter(Customer.id == customer_with_data.id).first()
        assert customer is not None
    
    def test_data_deletion_removes_all_data(self, authenticated_admin_client, customer_with_data, db_session):
        """Data deletion removes customer, cases, documents, events, and reminders."""
        # Get the case IDs before deletion
        case_ids = [case.id for case in customer_with_data.cases]
        
        # Delete the customer
        response = authenticated_admin_client.post("/admin/delete-customer", data={
            "customer_id": customer_with_data.id,
            "confirmation": "delete"
        }, follow_redirects=False)
        
        assert response.status_code == 200
        content = response.content.decode().lower()
        assert "permanently deleted" in content or "success" in content
        
        # Verify all data is removed
        customer = db_session.query(Customer).filter(Customer.id == customer_with_data.id).first()
        assert customer is None
        
        cases = db_session.query(Case).filter(Case.customer_id == customer_with_data.id).all()
        assert len(cases) == 0
        
        documents = db_session.query(Document).filter(Document.case_id.in_(case_ids)).all()
        assert len(documents) == 0
        
        events = db_session.query(Event).filter(Event.case_id.in_(case_ids)).all()
        assert len(events) == 0
        
        reminders = db_session.query(PendingReminder).filter(PendingReminder.case_id.in_(case_ids)).all()
        assert len(reminders) == 0
    
    def test_data_deletion_logs_event_before_deletion(self, authenticated_admin_client, customer_with_data, db_session):
        """Data deletion logs a 'customer_deleted' event before removing the customer."""
        # Get the case IDs before deletion
        case_ids = [case.id for case in customer_with_data.cases]
        
        # Delete the customer
        response = authenticated_admin_client.post("/admin/delete-customer", data={
            "customer_id": customer_with_data.id,
            "confirmation": "delete"
        }, follow_redirects=False)
        
        assert response.status_code == 200
        
        # Check for the deletion event (it should still exist even though customer is deleted)
        deletion_event = db_session.query(Event).filter(
            Event.event_type == "customer_deleted"
        ).first()
        
        assert deletion_event is not None
        assert customer_with_data.full_name in deletion_event.description
    
    def test_data_deletion_only_deletes_own_office_customers(self, authenticated_admin_client, db_session, test_office):
        """Data deletion only affects customers from the admin's own office."""
        # Create a customer for a different office
        from app.models.models import Office, Staff
        other_office = Office(
            name="Other Office",
            code="OTHER",
            display_name="Other Office"
        )
        db_session.add(other_office)
        db_session.flush()
        
        other_customer = Customer(
            office_id=other_office.id,
            full_name="Other Customer",
            phone="555-8888"
        )
        db_session.add(other_customer)
        db_session.commit()
        
        # Try to delete the other office's customer
        response = authenticated_admin_client.post("/admin/delete-customer", data={
            "customer_id": other_customer.id,
            "confirmation": "delete"
        }, follow_redirects=False)
        
        assert response.status_code == 200
        assert b"Customer not found" in response.content
        
        # Verify other customer still exists
        customer = db_session.query(Customer).filter(Customer.id == other_customer.id).first()
        assert customer is not None
    
    def test_data_deletion_nonexistent_customer(self, authenticated_admin_client):
        """Trying to delete non-existent customer shows error."""
        response = authenticated_admin_client.post("/admin/delete-customer", data={
            "customer_id": 99999,  # Non-existent ID
            "confirmation": "delete"
        }, follow_redirects=False)
        
        assert response.status_code == 200
        assert b"Customer not found" in response.content
