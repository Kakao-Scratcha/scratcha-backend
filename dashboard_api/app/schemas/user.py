# backend/dashboard_api/app/schemas/user.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from pydantic.alias_generators import to_camel


class UserCreate(BaseModel):  # 사용자 회원가입 스키마
    email: EmailStr = Field(..., example="유저 이메일")
    password: str = Field(..., min_length=8, max_length=20,
                          examples=["비밀번호 (8~20자)"])
    userName: str = Field(..., examples=["유저 이름"])


class UserLogin(BaseModel):  # 사용자 로그인 스키마
    email: EmailStr = Field(..., example="유저 이메일")
    password: str = Field(..., min_length=8, max_length=20,
                          examples=["비밀번호 (8~20자)"])  # 8~20자 사이


class UserUpdate(BaseModel):  # 사용자 업데이트 스키마
    userName: Optional[str] = None  # 사용자 이름
    # email: Optional[EmailStr] = None # 이메일 변경을 허용하려면 추가 (주의: 중복 확인 등 로직 필요)
    # password: Optional[str] = None # 비밀번호 변경은 별도의 엔드포인트/로직 권장 (현재는 없음)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    userName: str
    role: str
    createdAt: datetime
    deletedAt: Optional[datetime]  # 소프트 딜리트

    class Config:
        from_attribution = True  # Pydantic v2: orm_mode 대신 from_attributes 사용
        alias_generator = to_camel  # 카멜케이스 유지
        populate_by_name = True
