# schemas/application.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from app.schemas.api_key import ApiKeyResponse

# 애플리케이션 생성 요청 스키마


class ApplicationCreate(BaseModel):
    appName: str = Field(
        ...,
        min_length=1,
        max_length=100,
        example="애플리케이션 이름"
    )
    description: Optional[str] = Field(
        ...,
        max_length=500,
        example="애플리케이션 설명"
    )
    expiresPolicy: int = Field(
        ...,
        description="API 키 만료 정책(일 단위). 0 또는 음수는 무제한을 의미합니다.",
        example=0
    )

# 애플리케이션 업데이트 요청 스키마


class ApplicationUpdate(BaseModel):

    appName: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        example="애플리케이션 이름"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        example="애플리케이션 설명"
    )

# 애플리케이션 응답 스키마


class ApplicationResponse(BaseModel):
    id: int
    userId: int
    appName: str
    description: Optional[str]
    key: Optional[ApiKeyResponse] = None  # API 키 정보 (선택적)
    createdAt: datetime
    updatedAt: datetime
    deletedAt: Optional[datetime]

    class Config:
        from_attributes = True  # Pydantic v2: orm_mode 대신 from_attributes 사용
