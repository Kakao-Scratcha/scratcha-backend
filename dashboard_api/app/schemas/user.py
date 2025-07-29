# backend/dashboard_api/app/schemas/user.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from pydantic.alias_generators import to_camel


class UserCreate(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=8, max_length=20,
                          examples=["password123"])  # 8~20자 사이
    userName: str = Field(...,)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    userName: str = Field(..., alias="userName")
    createdAt: datetime = Field(..., alias="createdAt")
    deletedAt: Optional[datetime] = Field(None, alias="deletedAt")

    class Config:
        from_attribution = True  # Pydantic v2: orm_mode 대신 from_attributes 사용
        alias_generator = to_camel
        populate_by_name = True
