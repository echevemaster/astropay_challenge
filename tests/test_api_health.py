"""Tests for health check API endpoints."""
import pytest


class TestHealthAPI:
    """Test health check API endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "redis" in data
        assert "elasticsearch" in data
        assert "kafka" in data
    
    def test_health_check_status_values(self, client):
        """Test that health check returns valid status values."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Status should be "healthy" or "unhealthy"
        assert data["status"] in ["healthy", "unhealthy"]
        assert data["database"] in ["healthy", "unhealthy"]
        assert data["redis"] in ["healthy", "unhealthy"]
        assert data["elasticsearch"] in ["healthy", "unhealthy"]
        assert data["kafka"] in ["healthy", "unhealthy", "degraded"]

