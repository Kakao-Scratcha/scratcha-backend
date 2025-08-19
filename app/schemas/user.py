# backend/schemas/user.py

from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator
from pydantic.fields import FieldInfo

from pydantic.alias_generators import to_camel

from app.models.user import UserRole, UserSubscription


class UserCreate(BaseModel):  # 사용자 회원가입 스키마
    email: EmailStr = Field(
        ...,
        min_length=5,
        max_length=256,
        example="user@example.com"
    )
    password: Annotated[str, StringConstraints(min_length=8, max_length=64, pattern=r"^[\S]+$")] = Field(
        ...,
        examples=["password123!@#"]
    )
    userName: Annotated[str, StringConstraints(min_length=1, max_length=30, pattern=r"^[가-힣a-zA-Z0-9]+$")] = Field(
        ...,
        examples=["홍길동"]
    )

    @field_validator('password')
    @classmethod
    def validate_password_not_only_digits(cls, v):
        if v.isdigit():
            raise ValueError('Password cannot consist only of digits')
        return v

    @field_validator('userName')
    @classmethod
    def validate_username_not_only_digits(cls, v):
        if v.isdigit():
            raise ValueError('Username cannot consist only of digits')
        return v


class UserLogin(BaseModel):  # 사용자 로그인 스키마
    email: EmailStr = Field(
        ...,
        example="user@example.com"
    )
    password: Annotated[str, StringConstraints(min_length=8, max_length=64)] = Field(
        ...,
        examples=["password123!@#"]
    )  # 8~64자 사이


class UserUpdate(BaseModel):  # 사용자 업데이트 스키마
    userName: Optional[str] = Field(
        None,
        examples=["홍길동"],
        min_length=1,
        max_length=30
    )
    currnetPassword: Optional[str] = Field(
        None,
        title="현재 비밀번호",
        examples=["password123!@#"],
        min_length=8,
        max_length=20
    )
    newPassword: Optional[str] = Field(
        None,
        title="새 비밀번호",
        examples=["newpassword123!@#"],
        min_length=8,
        max_length=20
    )
    confirmPassword: Optional[str] = Field(
        None,
        title="새 비밀번호 확인",
        examples=["newpassword123!@#"],
        min_length=8,
        max_length=20
    )


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    userName: str
    role: UserRole
    plan: UserSubscription
    token: int
    createdAt: datetime
    updatedAt: datetime
    deletedAt: Optional[datetime]  # 소프트 딜리트

    class Config:
        from_attributes = True  # Pydantic v2: orm_mode 대신 from_attributes 사용
        alias_generator = to_camel  # 카멜케이스 유지
        populate_by_name = True


class UserPlanUpdate(BaseModel):
    plan: UserSubscription = Field(
        ...,
        description="업데이트할 사용자 구독 플랜",
        example="PRO"
    )
