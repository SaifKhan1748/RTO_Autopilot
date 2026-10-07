"""
Account lockout tests - ensure failed login attempts trigger lockout.
"""
import pytest
import bcrypt
from datetime import datetime, timedelta
from app.models.models import Staff


class TestAccountLockout:
    """Test account lockout after failed login attempts."""
    
    def test_account_locks_after_5_failed_attempts(self, test_client, test_staff):
        """Test that account locks after 5 failed login attempts."""
        # Make 5 failed login attempts
        for i in range(5):
            response = test_client.post("/login", data={
                "email": test_staff.email,
                "password": "wrongpassword"
            }, follow_redirects=False)
            assert response.status_code == 200
        
        # 6th attempt should show account locked message
        response = test_client.post("/login", data={
            "email": test_staff.email,
            "password": "wrongpassword"
        }, follow_redirects=False)
        
        assert response.status_code == 200
        assert b"Account locked" in response.content or b"too many failed attempts" in response.content
    
    def test_successful_login_resets_failed_attempts(self, test_client, test_staff, db_session):
        """Test that successful login resets failed login attempts."""
        # Make 3 failed login attempts
        for i in range(3):
            test_client.post("/login", data={
                "email": test_staff.email,
                "password": "wrongpassword"
            }, follow_redirects=False)
        
        # Verify failed attempts increased
        db_session.refresh(test_staff)
        assert test_staff.failed_login_attempts == 3
        
        # Successful login
        response = test_client.post("/login", data={
            "email": test_staff.email,
            "password": "testpassword123"
        }, follow_redirects=False)
        
        assert response.status_code == 303
        
        # Verify failed attempts reset
        db_session.refresh(test_staff)
        assert test_staff.failed_login_attempts == 0
        assert test_staff.locked_until is None
    
    def test_locked_account_cannot_login_even_with_correct_password(self, test_client, test_staff, db_session):
        """Test that locked account cannot login even with correct password."""
        # Manually lock the account
        test_staff.failed_login_attempts = 5
        test_staff.locked_until = datetime.utcnow() + timedelta(minutes=15)
        db_session.commit()
        
        # Try to login with correct password
        response = test_client.post("/login", data={
            "email": test_staff.email,
            "password": "testpassword123"
        }, follow_redirects=False)
        
        assert response.status_code == 200
        assert b"Account locked" in response.content
    
    def test_lockout_expires_after_cooldown(self, test_client, test_staff, db_session):
        """Test that lockout expires after the cooldown period."""
        # Lock the account with expired lockout time
        test_staff.failed_login_attempts = 5
        test_staff.locked_until = datetime.utcnow() - timedelta(minutes=1)  # Expired 1 minute ago
        db_session.commit()
        
        # Should be able to login now
        response = test_client.post("/login", data={
            "email": test_staff.email,
            "password": "testpassword123"
        }, follow_redirects=False)
        
        assert response.status_code == 303
