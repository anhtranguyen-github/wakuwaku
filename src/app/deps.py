from typing import Optional
from fastapi import Depends, HTTPException, status, Header

security = HTTPBearer()


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Get current user from authorization header.
    For local dev: accepts 'test' token and returns test user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.replace("Bearer ", "")
    if token == "test" or token == "test_token_123":
        return {"id": "550e8400-e29b-41d4-a716-446655440000", "email": "test@example.com"}
    return {"id": token}
