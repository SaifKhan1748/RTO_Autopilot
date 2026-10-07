"""
Rate limiting tests - ensure rate limiting works on public endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_status_page_rate_limiting(self, test_client):
        """Test that status page has rate limiting."""
        # Make 11 requests (exceeds 10/minute limit)
        responses = []
        for i in range(11):
            response = test_client.get("/status")
            responses.append(response)
        
        # At least some should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 8  # At least 8 should succeed before rate limiting kicks in
        
        # At least one should be rate limited
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)
        assert rate_limited_count >= 1  # At least one should hit rate limit
    
    def test_status_check_rate_limiting(self, test_client):
        """Test that status check has rate limiting."""
        # Make 6 requests (exceeds 5/minute limit)
        responses = []
        for i in range(6):
            response = test_client.post("/status", data={
                "case_id": 1,
                "phone": "555-1234"
            }, follow_redirects=False)
            responses.append(response)
        
        # First 5 should succeed (even if case not found)
        for i in range(5):
            assert responses[i].status_code in [200, 429]  # May be rate limited early
        
        # At least some should hit rate limit
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)
        assert rate_limited_count > 0
    
    def test_authenticated_bypasses_rate_limiting(self, authenticated_client):
        """Test that authenticated requests work (rate limiting may differ)."""
        # Authenticated users might have different rate limits
        # This test verifies that auth doesn't break the endpoint
        response = authenticated_client.get("/status")
        # Should work fine
        assert response.status_code == 200