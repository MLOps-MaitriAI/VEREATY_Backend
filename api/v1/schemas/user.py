from enum import Enum
from pydantic import BaseModel, EmailStr
from typing import Optional

class StatusEnum(str, Enum):
    pending_verification = "pending_verification"
    active = "active"
    inactive = "inactive"

class UserType(str, Enum):     
    user = "user" 
    master_admin = "master_admin" 

class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    #phone_number: Optional[str] = None
    