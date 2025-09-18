# backend/schemas/user.py

from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator
from pydantic.fields import FieldInfo
import re

from pydantic.alias_generators import to_camel

from app.models.user import UserRole


class UserCreate(BaseModel):  # 사용자 회원가입 스키마
    email: str = Field(
        ...,
        description="사용자 이메일 주소",
        example="user@example.com"
    )
    password: str = Field(
        ...,
        description="사용자 비밀번호",
        example="password123!@#"
    )
    userName: str = Field(
        ...,
        description="사용자 이름",
        example="홍길동"
    )

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        # 이메일 앞뒤 공백 제거 및 소문자 변환
        v = v.strip().lower()
        if len(v) > 254:
            raise ValueError("이메일은 254자 이내로 입력해주세요.")
        if not re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", v):
            raise ValueError("올바른 이메일 주소 형식이 아닙니다.")
        return v

    @field_validator('userName')
    @classmethod
    def validate_username(cls, v):
        if not 1 <= len(v) <= 30:
            raise ValueError("이름은 1~30자 이내로 입력해주세요.")
        if v.isdigit():
            raise ValueError("이름은 숫자만으로 구성할 수 없습니다.")
        if re.search(r'[^가-힣A-Za-z0-9._-]', v):
            raise ValueError("이름은 한글, 영문, 숫자, 특수문자(.-_) 만 사용할 수 있습니다.")
        if v.startswith(('.', '_', '-')) or v.endswith(('.', '_', '-')):
            raise ValueError("이름은 특수문자로 시작하거나 끝낼 수 없습니다.")
        if re.search(r'[._-]{2,}', v):
            raise ValueError("이름에 특수문자는 연속으로 사용할 수 없습니다.")
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not 8 <= len(v) <= 64:
            raise ValueError("비밀번호는 8~64자 이내로 입력해주세요.")
        if v.isdigit():
            raise ValueError("비밀번호는 숫자만으로 구성할 수 없습니다.")
        if not re.match(r'^[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};:,./?]+$', v):
            raise ValueError("비밀번호에 허용되지 않는 문자(공백 등)가 포함되어 있습니다.")
        return v


class UserLogin(BaseModel):  # 사용자 로그인 스키마
    email: EmailStr = Field(
        ...,
        description="가입된 사용자 이메일 주소",
        example="user@example.com"
    )
    password: Annotated[str, StringConstraints(min_length=8, max_length=64)] = Field(
        ...,
        description="가입된 사용자 비밀번호",
        example="password123!@#"
    )  # 8~64자 사이

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        # 이메일 앞뒤 공백 제거 및 소문자 변환
        v = v.strip().lower()
        if len(v) > 254:
            raise ValueError("이메일은 254자 이내로 입력해주세요.")
        if not re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", v):
            raise ValueError("올바른 이메일 주소 형식이 아닙니다.")
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not 8 <= len(v) <= 64:
            raise ValueError("비밀번호는 8~64자 이내로 입력해주세요.")
        if v.isdigit():
            raise ValueError("비밀번호는 숫자만으로 구성할 수 없습니다.")
        if not re.match(r'^[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};:,./?]+$', v):
            raise ValueError("비밀번호에 허용되지 않는 문자(공백 등)가 포함되어 있습니다.")
        return v


class UserUpdate(BaseModel):  # 사용자 업데이트 스키마
    userName: Optional[str] = Field(
        None,
        description="새로운 사용자 이름",
        example="새로운 홍길동"
    )
    currnetPassword: Optional[str] = Field(
        None,
        description="현재 비밀번호",
        example="password123!@#",
    )
    newPassword: Optional[str] = Field(
        None,
        description="새로운 비밀번호",
        example="newpassword123!@#",
    )
    confirmPassword: Optional[str] = Field(
        None,
        description="새로운 비밀번호 확인",
        example="newpassword123!@#",
    )

    @field_validator('userName')
    @classmethod
    def validate_username(cls, v):
        if v is None:
            return v
        if not 1 <= len(v) <= 30:
            raise ValueError("이름은 1~30자 이내로 입력해주세요.")
        if v.isdigit():
            raise ValueError("이름은 숫자만으로 구성할 수 없습니다.")
        if re.search(r'[^가-힣A-Za-z0-9._-]', v):
            raise ValueError("이름은 한글, 영문, 숫자, 특수문자(.-_) 만 사용할 수 있습니다.")
        if v.startswith(('.', '_', '-')) or v.endswith(('.', '_', '-')):
            raise ValueError("이름은 특수문자로 시작하거나 끝낼 수 없습니다.")
        if re.search(r'[._-]{2,}', v):
            raise ValueError("이름에 특수문자는 연속으로 사용할 수 없습니다.")
        return v

    @field_validator('newPassword')
    @classmethod
    def validate_new_password(cls, v):
        if not 8 <= len(v) <= 64:
            raise ValueError("비밀번호는 8~64자 이내로 입력해주세요.")
        if v.isdigit():
            raise ValueError("비밀번호는 숫자만으로 구성할 수 없습니다.")
        if not re.match(r'^[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};:,./?]+$', v):
            raise ValueError("비밀번호에 허용되지 않는 문자(공백 등)가 포함되어 있습니다.")
        return v

    @field_validator('confirmPassword')
    @classmethod
    def validate_confirm_password(cls, v):
        if not 8 <= len(v) <= 64:
            raise ValueError("비밀번호는 8~64자 이내로 입력해주세요.")
        if v.isdigit():
            raise ValueError("비밀번호는 숫자만으로 구성할 수 없습니다.")
        if not re.match(r'^[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};:,./?]+$', v):
            raise ValueError("비밀번호에 허용되지 않는 문자(공백 등)가 포함되어 있습니다.")
        return v


class UserResponse(BaseModel):
    id: int = Field(..., description="사용자의 고유 식별자", example=1)
    email: EmailStr = Field(..., description="사용자 이메일 주소",
                            example="user@example.com")
    userName: str = Field(..., description="사용자 이름", example="홍길동")
    role: UserRole = Field(..., description="사용자 역할", example="user")
    # plan: UserSubscription = Field(...,description="사용자 구독 플랜", example="free")
    token: int = Field(..., description="사용자의 현재 토큰(크레딧) 잔액", example=1000)
    createdAt: datetime = Field(..., description="사용자 계정 생성 일시",
                                example="2024-01-01T12:00:00")
    updatedAt: datetime = Field(..., description="사용자 정보 마지막 수정 일시",
                                example="2024-01-01T12:00:00")
    deletedAt: Optional[datetime] = Field(
        None, description="사용자 계정 삭제 일시 (소프트 삭제)", example=None)

    class Config:
        from_attributes = True  # Pydantic v2: orm_mode 대신 from_attributes 사용
        alias_generator = to_camel  # 카멜케이스 유지
        populate_by_name = True


# class UserPlanUpdate(BaseModel):
#     plan: UserSubscription = Field(
#         ...,
#         description="업데이트할 사용자 구독 플랜",
#         example="pro"
#     )
