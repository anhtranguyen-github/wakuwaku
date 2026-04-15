from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    email: str
    username: Optional[str] = None

class UserCreate(UserBase):
    password: Optional[str] = None

class UserResponse(UserBase):
    id: str
    username: Optional[str] = None

    model_config = {
        "from_attributes": True
    }
