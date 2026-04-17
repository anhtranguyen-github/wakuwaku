from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    email: str
    username: Optional[str] = None

class UserCreate(UserBase):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(UserBase):
    id: str
    username: Optional[str] = None

    model_config = {
        "from_attributes": True
    }
