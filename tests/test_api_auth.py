"""Tests for authentication API endpoints."""
import pytest
from jose import jwt
from app.config import settings


class TestAuthAPI:
    """Test authentication API endpoints."""
    
    def test_get_token(self, client):
        """Test getting JWT token."""
        response = client.post(
            "/api/v1/auth/token",
            json={"user_id": "test_user_123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    def test_get_token_invalid_request(self, client):
        """Test getting token with invalid request."""
        response = client.post(
            "/api/v1/auth/token",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_me_with_token(self, client, auth_token):
        """Test getting current user info with valid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user_123"
    
    def test_get_me_without_token(self, client):
        """Test getting current user info without token."""
        response = client.get("/api/v1/auth/me")
        
        # FastAPI HTTPBearer returns 403 when credentials are missing
        assert response.status_code in [401, 403]
    
    def test_get_me_invalid_token(self, client):
        """Test getting current user info with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_token_contains_user_id(self, client):
        """Test that token contains correct user_id."""
        response = client.post(
            "/api/v1/auth/token",
            json={"user_id": "test_user_456"}
        )
        
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        # Decode token
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        assert payload["sub"] == "test_user_456"
    
    def test_token_expiration(self, client):
        """Test that token has expiration."""
        response = client.post(
            "/api/v1/auth/token",
            json={"user_id": "test_user_123"}
        )
        
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        # Decode token
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        assert "exp" in payload

