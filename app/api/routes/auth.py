"""Authentication routes for JWT token generation."""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import timedelta
from app.auth import create_access_token, get_current_user_id
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

security = HTTPBearer()


class TokenRequest(BaseModel):
    """Request model for token generation."""
    user_id: str


class TokenResponse(BaseModel):
    """Response model for token generation."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/token", response_model=TokenResponse)
async def create_token(request: TokenRequest):
    """
    Generate a JWT token for a user.
    
    **Note:** In production, this endpoint should validate user credentials.
    This is a simplified version for development/testing purposes.
    """
    # In production, validate user credentials here
    # For now, we'll just create a token for any user_id provided
    
    access_token_expires = timedelta(minutes=settings.jwt_expire_minutes)
    access_token = create_access_token(
        data={"sub": request.user_id, "user_id": request.user_id},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60
    )


@router.get("/me")
async def get_current_user_info(
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get current authenticated user information.
    
    Returns the user_id from the JWT token.
    """
    return {
        "user_id": current_user_id
    }

