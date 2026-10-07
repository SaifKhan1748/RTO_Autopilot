"""
Password reset tests - ensure forgot password flow works correctly.
"""
import pytest
import bcrypt
from datetime import datetime, timedelta
from app.models.models import PasswordReset


class TestPasswordReset:
    """Test password reset functionality."""
    
    def test_forgot_password_page_loads(self, test_client):
        """Test that forgot password page loads successfully."""
        response = test_client.get("/forgot-password")
        assert response.status_code == 200
        assert b"Forgot your password" in response.content
    
    def test_forgot_password_with_valid_email(self, test_client, test_staff):
        """Test forgot password with valid email (doesn't reveal if email exists)."""
        response = test_client.post("/forgot-password", data={
            "email": test_staff.email
        }, follow_redirects=False)
        
        assert response.status_code == 200
        # Should show success message regardless of whether email exists
        assert b"password reset link" in response.content or b"has been sent" in response.content
    
    def test_forgot_password_with_invalid_email(self, test_client):
        """Test forgot password with invalid email (security - doesn't reveal)."""
        response = test_client.post("/forgot-password", data={
            "email": "nonexistent@example.com"
        }, follow_redirects=False)
        
        assert response.status_code == 200
        # Should show same success message for security
        assert b"password reset link" in response.content or b"has been sent" in response.content
    
    def test_reset_password_with_valid_token(self, test_client, test_staff, db_session):
        """Test password reset with valid token."""
        # Create a password reset token
        import secrets
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        password_reset = PasswordReset(
            staff_id=test_staff.id,
            token=token,
            expires_at=expires_at
        )
        db_session.add(password_reset)
        db_session.commit()
        
        # Reset password
        response = test_client.post("/reset-password", data={
            "token": token,
            "new_password": "newpassword123",
            "confirm_password": "newpassword123"
        }, follow_redirects=False)
        
        assert response.status_code == 200
        # Should redirect to login page with success message
        assert b"Login" in response.content  # Check we're on login page
        
        # Verify password was actually changed by checking the database
        db_session.refresh(test_staff)
        import bcrypt
        # Verify the new password works
        assert bcrypt.checkpw("newpassword123".encode('utf-8'), test_staff.password_hash.encode('utf-8'))
    
    def test_reset_password_with_mismatched_passwords(self, test_client, test_staff, db_session):
        """Test password reset with mismatched passwords."""
        # Create a password reset token
        import secrets
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        password_reset = PasswordReset(
            staff_id=test_staff.id,
            token=token,
            expires_at=expires_at
        )
        db_session.add(password_reset)
        db_session.commit()
        
        # Try to reset with mismatched passwords
        response = test_client.post("/reset-password", data={
            "token": token,
            "new_password": "newpassword123",
            "confirm_password": "differentpassword"
        }, follow_redirects=False)
        
        assert response.status_code == 200
        assert b"do not match" in response.content
    
    def test_reset_password_with_expired_token(self, test_client, test_staff, db_session):
        """Test password reset with expired token."""
        # Create an expired password reset token
        import secrets
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired
        
        password_reset = PasswordReset(
            staff_id=test_staff.id,
            token=token,
            expires_at=expires_at
        )
        db_session.add(password_reset)
        db_session.commit()
        
        # Try to reset with expired token
        response = test_client.post("/reset-password", data={
            "token": token,
            "new_password": "newpassword123",
            "confirm_password": "newpassword123"
        }, follow_redirects=False)
        
        assert response.status_code == 200
        assert b"Invalid or expired" in response.content
    
    def test_reset_password_unlocks_account(self, test_client, test_staff, db_session):
        """Test that password reset unlocks a locked account."""
        # Lock the account
        test_staff.failed_login_attempts = 5
        test_staff.locked_until = datetime.utcnow() + timedelta(minutes=15)
        db_session.commit()
        
        # Create a password reset token
        import secrets
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        password_reset = PasswordReset(
            staff_id=test_staff.id,
            token=token,
            expires_at=expires_at
        )
        db_session.add(password_reset)
        db_session.commit()
        
        # Reset password
        test_client.post("/reset-password", data={
            "token": token,
            "new_password": "newpassword123",
            "confirm_password": "newpassword123"
        }, follow_redirects=False)
        
        # Verify account is unlocked
        db_session.refresh(test_staff)
        assert test_staff.failed_login_attempts == 0
        assert test_staff.locked_until is None
        
        # Should be able to login with new password
        response = test_client.post("/login", data={
            "email": test_staff.email,
            "password": "newpassword123"
        }, follow_redirects=False)
        
        assert response.status_code == 303
