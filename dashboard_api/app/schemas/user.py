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


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """
    사용자 프로필 업데이트 요청에 사용되는 스키마입니다.
    이메일은 변경 불가능하게 하거나, 별도의 복잡한 인증 절차를 거치도록 하는 것이 일반적입니다.
    """
    userName: Optional[str] = None  # 사용자 이름
    # email: Optional[EmailStr] = None # 이메일 변경을 허용하려면 추가 (주의: 중복 확인 등 로직 필요)
    # password: Optional[str] = None # 비밀번호 변경은 별도의 엔드포인트/로직 권장 (현재는 없음)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    userName: str
    createdAt: datetime
    deletedAt: Optional[datetime]

    class Config:
        from_attribution = True  # Pydantic v2: orm_mode 대신 from_attributes 사용
        alias_generator = to_camel
        populate_by_name = True
