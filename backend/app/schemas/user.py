from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime

# ==========================================
# DEPARTMENT SCHEMAS
# ==========================================
class DepartmentBase(BaseModel):
    name: str = Field(..., max_length=100, description="Department display name")
    code: str = Field(..., max_length=10, description="Unique department code (e.g. ENG, HR)")

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# ROLE SCHEMAS
# ==========================================
class RoleResponse(BaseModel):
    id: str
    description: str
    permissions: List[str]

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# USER SCHEMAS
# ==========================================
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., max_length=100)
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Plaintext password")
    role_id: str = Field("ENGINEER", description="Role code assigned to user")
    department_id: Optional[uuid.UUID] = Field(None, description="Department scope")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: uuid.UUID
    role_id: str
    department_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserResponseWithRelations(UserResponse):
    department: Optional[DepartmentResponse] = None
    role: RoleResponse

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# AUTH SCHEMAS
# ==========================================
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str
    exp: int
    type: str
