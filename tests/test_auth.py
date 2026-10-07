"""
Authentication tests.
"""
import pytest
from fastapi.testclient import TestClient


class TestLogin:
    """Test login functionality."""
    
    def test_login_with_correct_credentials(self, test_client, test_staff):
        """Test that login works with correct credentials."""
        response = test_client.post("/login", data={
            "email": test_staff.email,
            "password": "testpassword123"
        }, follow_redirects=False)
        
        # Should redirect to dashboard on successful login
        assert response.status_code == 303
        assert response.headers.get("location") == "/dashboard"
        
        # Verify session is set by checking if we can access dashboard
        dashboard_response = test_client.get("/dashboard")
        assert dashboard_response.status_code == 200
    
    def test_login_with_wrong_password(self, test_client, test_staff):
        """Test that login fails with wrong password."""
        response = test_client.post("/login", data={
            "email": test_staff.email,
            "password": "wrongpassword"
        }, follow_redirects=False)
        
        # Should stay on login page with error
        assert response.status_code == 200
        assert b"Invalid email or password" in response.content
    
    def test_login_with_wrong_email(self, test_client):
        """Test that login fails with non-existent email."""
        response = test_client.post("/login", data={
            "email": "nonexistent@example.com",
            "password": "anypassword"
        }, follow_redirects=False)
        
        # Should stay on login page with error
        assert response.status_code == 200
        assert b"Invalid email or password" in response.content
    
    def test_login_with_inactive_account(self, test_client, test_office, db_session):
        """Test that login fails with inactive account."""
        import bcrypt
        from app.models.models import Staff
        
        # Create inactive staff
        password_hash = bcrypt.hashpw("testpassword123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        inactive_staff = Staff(
            office_id=test_office.id,
            email="inactive@example.com",
            password_hash=password_hash,
            full_name="Inactive Staff",
            role="staff",
            is_active=0  # Inactive
        )
        db_session.add(inactive_staff)
        db_session.commit()
        
        response = test_client.post("/login", data={
            "email": "inactive@example.com",
            "password": "testpassword123"
        }, follow_redirects=False)
        
        # Should stay on login page with error
        assert response.status_code == 200
        assert b"Account is inactive" in response.content
    
    def test_logout_clears_session(self, authenticated_client):
        """Test that logout clears the session."""
        # Logout
        response = authenticated_client.get("/logout", follow_redirects=False)
        assert response.status_code in [303, 307]  # Accept both redirect codes
        assert response.headers.get("location") == "/login"
        
        # Try to access dashboard - should redirect to login
        dashboard_response = authenticated_client.get("/dashboard", follow_redirects=False)
        assert dashboard_response.status_code in [303, 307]  # Accept both redirect codes
        assert dashboard_response.headers.get("location") == "/login"
    
    def test_protected_route_without_login(self, test_client):
        """Test that protected routes redirect to login when not authenticated."""
        response = test_client.get("/dashboard", follow_redirects=False)
        assert response.status_code in [303, 307]  # Accept both redirect codes
        assert response.headers.get("location") == "/login"
