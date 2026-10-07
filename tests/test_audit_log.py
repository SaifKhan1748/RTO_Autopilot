"""
Audit log tests - ensure admin-only audit log viewer works correctly.
"""
import pytest
from app.models.models import Event, Staff
import bcrypt


class TestAuditLog:
    """Test audit log viewer functionality."""
    
    @pytest.fixture
    def admin_staff(self, db_session, test_office):
        """Create an admin staff member."""
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
    def sample_events(self, db_session, test_office, test_customer):
        """Create sample events for testing."""
        # Create a case for the customer
        from app.models.models import Case
        case = Case(
            office_id=test_office.id,
            customer_id=test_customer.id,
            service_type="New Registration",
            status="new"
        )
        db_session.add(case)
        db_session.flush()
        
        # Create sample events
        events = [
            Event(
                case_id=case.id,
                office_id=test_office.id,
                event_type="case_created",
                description="Case created",
                created_by="admin@example.com"
            ),
            Event(
                case_id=case.id,
                office_id=test_office.id,
                event_type="status_changed",
                description="Status changed to in_progress",
                created_by="staff@example.com"
            ),
            Event(
                case_id=case.id,
                office_id=test_office.id,
                event_type="document_uploaded",
                description="Document uploaded",
                created_by="admin@example.com"
            )
        ]
        
        for event in events:
            db_session.add(event)
        
        db_session.commit()
        return events
    
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
    
    def test_admin_can_access_audit_log(self, authenticated_admin_client):
        """Admin can access audit log page."""
        response = authenticated_admin_client.get("/admin/audit-log")
        assert response.status_code == 200
        assert b"Audit Log" in response.content
    
    def test_regular_staff_cannot_access_audit_log(self, authenticated_staff_client):
        """Regular staff cannot access audit log page."""
        response = authenticated_staff_client.get("/admin/audit-log")
        assert response.status_code == 200
        # Should be redirected to dashboard - check that it's dashboard content
        assert b"Dashboard" in response.content or b"Office Cases" in response.content
    
    def test_audit_log_shows_office_events_only(self, authenticated_admin_client, sample_events, db_session, test_office):
        """Audit log only shows events from the admin's office."""
        response = authenticated_admin_client.get("/admin/audit-log")
        assert response.status_code == 200
        
        # Get events from the response
        content = response.content.decode()
        
        # Should show events from our office
        assert "case_created" in content
        assert "status_changed" in content
    
    def test_audit_log_filters_by_case_id(self, authenticated_admin_client, sample_events, db_session):
        """Audit log can filter by case ID."""
        # Get the case ID from the first event
        case_id = sample_events[0].case_id
        
        response = authenticated_admin_client.get(f"/admin/audit-log?case_id={case_id}")
        assert response.status_code == 200
        
        content = response.content.decode()
        # Should show filtered results - case ID should appear in the page
        assert str(case_id) in content
    
    def test_audit_log_filters_by_date_range(self, authenticated_admin_client, sample_events):
        """Audit log can filter by date range."""
        from datetime import datetime, timedelta
        
        # Get today's date in YYYY-MM-DD format
        today = datetime.now().strftime("%Y-%m-%d")
        
        response = authenticated_admin_client.get(f"/admin/audit-log?start_date={today}&end_date={today}")
        assert response.status_code == 200
    
    def test_audit_log_shows_recent_events_only(self, authenticated_admin_client, sample_events):
        """Audit log shows only the most recent 100 events."""
        response = authenticated_admin_client.get("/admin/audit-log")
        assert response.status_code == 200
        
        content = response.content.decode()
        # Should indicate it's showing recent events
        assert "Recent Events" in content
    
    def test_audit_log_shows_event_details(self, authenticated_admin_client, sample_events):
        """Audit log shows detailed event information."""
        response = authenticated_admin_client.get("/admin/audit-log")
        assert response.status_code == 200
        
        content = response.content.decode()
        # Should show event columns
        assert "Timestamp" in content
        assert "Event Type" in content
        assert "Description" in content
        assert "Created By" in content
    
    def test_audit_log_office_scoping(self, authenticated_admin_client, db_session, test_office):
        """Audit log is properly scoped to the admin's office."""
        # Create an event for a different office
        from app.models.models import Office, Customer, Case
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
        db_session.flush()
        
        other_case = Case(
            office_id=other_office.id,
            customer_id=other_customer.id,
            service_type="Transfer",
            status="new"
        )
        db_session.add(other_case)
        db_session.flush()
        
        other_event = Event(
            case_id=other_case.id,
            office_id=other_office.id,
            event_type="case_created",
            description="Other office case",
            created_by="other@example.com"
        )
        db_session.add(other_event)
        db_session.commit()
        
        # Get audit log - should not show other office's events
        response = authenticated_admin_client.get("/admin/audit-log")
        assert response.status_code == 200
        
        content = response.content.decode()
        # Should not contain the other office's event description
        assert "Other office case" not in content