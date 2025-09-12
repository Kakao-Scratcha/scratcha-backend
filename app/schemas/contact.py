from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from pydantic.alias_generators import to_camel
import re


# 문의 베이스 스키마
class ContactBase(BaseModel):
    name: str = Field(..., max_length=50, description="작성자 이름", example="홍길동")
    email: EmailStr = Field(..., max_length=100,
                            description="작성자 이메일", example="user@example.com")
    title: str = Field(..., max_length=200,
                       description="문의 제목", example="서비스 관련 문의입니다.")
    content: str = Field(..., max_length=5000,
                         description="문의 내용", example="안녕하세요, ...")

    @field_validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('이름을 입력해주세요.')
        v = v.strip()
        if not 1 <= len(v) <= 50:
            raise ValueError("이름은 1~50자 이내로 입력해주세요.")
        if v.isdigit():
            raise ValueError("이름은 숫자만으로 구성할 수 없습니다.")
        if re.search(r'[^가-힣A-Za-z0-9._-]', v):
            raise ValueError("이름은 한글, 영문, 숫자, 특수문자(.-_) 만 사용할 수 있습니다.")
        if v.startswith(('.', '_', '-')) or v.endswith(('.', '_', '-')):
            raise ValueError("이름은 특수문자로 시작하거나 끝낼 수 없습니다.")
        if re.search(r'[._-]{2,}', v):
            raise ValueError("이름에 특수문자는 연속으로 사용할 수 없습니다.")
        return v

    @field_validator('email')
    def validate_email(cls, v):
        if not v or not v.strip():
            raise ValueError('이메일을 입력해주세요.')
        v = v.strip().lower()
        if len(v) > 100:
            raise ValueError("이메일은 100자 이내로 입력해주세요.")
        if not re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", v):
            raise ValueError("올바른 이메일 주소 형식이 아닙니다.")
        return v

    @field_validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('제목을 입력해주세요.')
        if len(v) > 200:
            raise ValueError('제목은 200자 이내로 입력해주세요.')
        return v

    @field_validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('내용을 입력해주세요.')
        if len(v) > 5000:
            raise ValueError('내용은 5000자 이내로 입력해주세요.')
        return v

# 문의 생성 스키마 (API 요청 시 사용)


class ContactCreate(ContactBase):
    pass


# 문의 응답 스키마 (API 응답 시 사용)
class ContactResponse(ContactBase):
    id: int = Field(..., description="문의 고유 ID", example=1)
    createdAt: datetime = Field(..., description="문의 생성 일시",
                                example="2024-01-01T12:00:00")

    class Config:
        from_attributes = True  # SQLAlchemy 모델을 Pydantic 모델로 변환
        alias_generator = to_camel  # alias를 camelCase로 자동 변환
        populate_by_name = True  # alias 이름으로도 값을 할당받을 수 있도록 설정
